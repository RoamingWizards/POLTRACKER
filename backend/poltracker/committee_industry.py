"""Deterministic committee/subcommittee <-> industry (SIC) relevance. Phase 2 of committee/sector context.

Answers one narrow question: is a company's industry within an area plausibly relevant to the jurisdiction of a committee or
subcommittee a politician sits on? It is a contextual relationship only. It is NOT evidence of wrongdoing or of non-public
information, it flags nothing, uses no market data and no language model, and makes no network call.

Every result comes from explicit mapping rows (data/committee_industry_mappings.json, loaded into committee_industry_mappings), each
with its official-jurisdiction citation, SIC range and rationale. Anything the mappings do not cover is `unknown`, never guessed.

Precedence: a subcommittee mapping is preferred over a parent committee mapping, then direct over related, then the narrower SIC range.
"""

import json
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import CommitteeAssignment, CommitteeIndustryMapping, _now

LEVELS = ("direct", "related", "none")
STATUSES = ("relevant", "not_relevant", "unknown")


class MappingError(ValueError):
    """A mapping file or row that is invalid. Nothing is loaded."""


@dataclass(frozen=True)
class Mapping:
    id: int
    chamber: str
    committee_code: str
    subcommittee_code: str | None
    committee_name: str
    subcommittee_name: str | None
    sic_start: int | None
    sic_end: int | None
    industry_pattern: str | None
    relevance_level: str
    rationale: str
    jurisdiction_text: str | None
    source_citation: str | None
    source_url: str
    reviewed_at: datetime | None
    mapping_version: str

    @property
    def scope(self) -> str:
        return "subcommittee" if self.subcommittee_code else "committee"

    @property
    def sic_range(self) -> str | None:
        return None if self.sic_start is None else f"{self.sic_start:04d}-{self.sic_end:04d}"


@dataclass(frozen=True)
class Assignment:
    committee_code: str
    committee_name: str = ""
    subcommittee_code: str | None = None
    subcommittee_name: str | None = None
    chamber: str = "house"


@dataclass(frozen=True)
class Match:
    """Why a security's industry is relevant to a committee/subcommittee, with full provenance."""

    mapping_id: int
    scope: str  # subcommittee | committee
    committee_code: str
    committee_name: str
    subcommittee_code: str | None
    subcommittee_name: str | None
    level: str  # direct | related
    sic_range: str
    rationale: str
    source_citation: str | None
    source_url: str
    jurisdiction_text: str | None
    mapping_version: str
    reviewed: bool


@dataclass
class Relevance:
    status: str  # relevant | not_relevant | unknown
    reason: str  # match | no_match | no_sic | no_committee_assignments | unmapped_committees
    mapping_version: str | None
    matches: list[Match] = field(default_factory=list)  # best first
    unmapped_committees: list[str] = field(default_factory=list)

    @property
    def primary(self) -> Match | None:
        return self.matches[0] if self.matches else None

    @property
    def level(self) -> str | None:
        return self.primary.level if self.primary else None


def parse_sic(value: object) -> int | None:
    text = str(value).strip() if value is not None else ""
    return int(text) if text.isdigit() and len(text) == 4 and int(text) > 0 else None


def _rank(m: Mapping) -> tuple:
    width = (m.sic_end - m.sic_start) if m.sic_start is not None else 0
    return (0 if m.subcommittee_code else 1, 0 if m.relevance_level == "direct" else 1, width, m.id)


class CommitteeIndustryMatcher:
    def __init__(self, mappings: Iterable[Mapping], version: str | None = None):
        mappings = list(mappings)
        if version is None and mappings:
            version = max(mappings, key=lambda m: m.id).mapping_version  # the most recently loaded version
        self.version = version
        self._rows = [m for m in mappings if m.mapping_version == version]
        self._by_committee: dict[str, list[Mapping]] = defaultdict(list)
        for m in self._rows:
            self._by_committee[m.committee_code].append(m)
        self._patterns = {m.id: re.compile(m.industry_pattern, re.I) for m in self._rows if m.industry_pattern}

    @property
    def mapped_committees(self) -> set[str]:
        return set(self._by_committee)

    def _applies(self, m: Mapping, sic: int, industry: str | None) -> bool:
        if m.relevance_level == "none" or m.sic_start is None or not m.sic_start <= sic <= m.sic_end:
            return False
        pattern = self._patterns.get(m.id)
        return pattern is None or bool(industry and pattern.search(industry))

    def evaluate(self, assignments: Iterable[Assignment], sic_code: object, industry: str | None = None) -> Relevance:
        sic = parse_sic(sic_code)
        if sic is None:
            return Relevance("unknown", "no_sic", self.version)
        seats = list(assignments)
        if not seats:
            return Relevance("unknown", "no_committee_assignments", self.version)
        committees = {a.committee_code: a.committee_name or a.committee_code for a in seats}
        subs = {(a.committee_code, a.subcommittee_code) for a in seats if a.subcommittee_code}
        unmapped = sorted(name for code, name in committees.items() if code not in self._by_committee)

        found: list[Mapping] = []
        for code in committees:
            for m in self._by_committee.get(code, []):
                if m.subcommittee_code and (code, m.subcommittee_code) not in subs:
                    continue  # a subcommittee mapping only applies to a member who sits on that subcommittee
                if self._applies(m, sic, industry):
                    found.append(m)
        if found:
            found.sort(key=_rank)
            return Relevance("relevant", "match", self.version, [_to_match(m) for m in found], unmapped)
        if len(unmapped) == len(committees):
            return Relevance("unknown", "unmapped_committees", self.version, [], unmapped)
        if unmapped:  # something unmapped could still be relevant, so "not relevant" cannot be asserted
            return Relevance("unknown", "unmapped_committees", self.version, [], unmapped)
        return Relevance("not_relevant", "no_match", self.version)


def _to_match(m: Mapping) -> Match:
    return Match(m.id, m.scope, m.committee_code, m.committee_name, m.subcommittee_code, m.subcommittee_name, m.relevance_level, m.sic_range or "",
                 m.rationale, m.source_citation, m.source_url, m.jurisdiction_text, m.mapping_version, m.reviewed_at is not None)


# --- loading -------------------------------------------------------------------------------------------------

REQUIRED = ("chamber", "committee_code", "committee_name", "relevance_level", "rationale", "source_url", "mapping_version")


def validate_rows(rows: list[dict]) -> None:
    if not isinstance(rows, list) or not rows:
        raise MappingError("the mapping file must be a non-empty JSON list")
    versions = {r.get("mapping_version") for r in rows if isinstance(r, dict)}
    if len(versions) != 1:
        raise MappingError(f"a mapping file must hold exactly one mapping_version, found {sorted(map(str, versions))}")
    for i, r in enumerate(rows, start=1):
        if not isinstance(r, dict):
            raise MappingError(f"row {i}: not an object")
        missing = [k for k in REQUIRED if not str(r.get(k) or "").strip()]
        if missing:
            raise MappingError(f"row {i}: missing {', '.join(missing)}")
        if r["relevance_level"] not in LEVELS:
            raise MappingError(f"row {i}: relevance_level must be one of {LEVELS}")
        start, end = r.get("sic_start"), r.get("sic_end")
        if r["relevance_level"] == "none":
            if start is not None or end is not None:
                raise MappingError(f"row {i}: a 'none' mapping has no SIC range")
        else:
            a, b = parse_sic(start), parse_sic(end)
            if a is None or b is None or a > b:
                raise MappingError(f"row {i}: sic_start/sic_end must be 4-digit SIC codes with start <= end")
        if r.get("industry_pattern"):
            try:
                re.compile(r["industry_pattern"])
            except re.error as exc:
                raise MappingError(f"row {i}: industry_pattern is not a valid regex ({exc})") from exc
        if r.get("subcommittee_code") and not str(r.get("subcommittee_name") or "").strip():
            raise MappingError(f"row {i}: a subcommittee mapping needs subcommittee_name")


def load_rows(path: Path) -> list[dict]:
    try:
        rows = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise MappingError(f"cannot read {path}: {exc}") from exc
    validate_rows(rows)
    return rows


def sync_mappings(session: Session, path: Path, now: datetime | None = None) -> tuple[str, int]:
    """Load one mapping version, replacing any existing rows of that same version (other versions are kept). Idempotent."""
    rows = load_rows(path)
    version = rows[0]["mapping_version"]
    session.execute(delete(CommitteeIndustryMapping).where(CommitteeIndustryMapping.mapping_version == version))
    for r in rows:
        reviewed = datetime.fromisoformat(r["reviewed_at"]) if r.get("reviewed_at") else None
        session.add(CommitteeIndustryMapping(
            chamber=r["chamber"], committee_code=r["committee_code"], subcommittee_code=r.get("subcommittee_code") or None,
            committee_name=r["committee_name"], subcommittee_name=r.get("subcommittee_name") or None,
            sic_start=parse_sic(r.get("sic_start")), sic_end=parse_sic(r.get("sic_end")), industry_pattern=r.get("industry_pattern") or None,
            relevance_level=r["relevance_level"], rationale=r["rationale"], jurisdiction_text=r.get("jurisdiction_text"),
            source_citation=r.get("source_citation"), source_url=r["source_url"], reviewed_at=reviewed, mapping_version=version,
            created_at=now or _now(),
        ))
    session.flush()
    return version, len(rows)


def load_mappings(session: Session, version: str | None = None) -> list[Mapping]:
    stmt = select(CommitteeIndustryMapping).order_by(CommitteeIndustryMapping.id)
    if version:
        stmt = stmt.where(CommitteeIndustryMapping.mapping_version == version)
    return [Mapping(r.id, r.chamber, r.committee_code, r.subcommittee_code, r.committee_name, r.subcommittee_name, r.sic_start, r.sic_end,
                    r.industry_pattern, r.relevance_level, r.rationale, r.jurisdiction_text, r.source_citation, r.source_url, r.reviewed_at,
                    r.mapping_version) for r in session.scalars(stmt)]


def load_assignments(session: Session, politician_id: int) -> list[Assignment]:
    rows = session.scalars(select(CommitteeAssignment).where(CommitteeAssignment.politician_id == politician_id))
    return [Assignment(r.committee_code, r.committee_name, r.subcommittee_code or None, r.subcommittee_name, r.chamber) for r in rows]
