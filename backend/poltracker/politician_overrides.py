"""Explicit, human-reviewed politician -> Bioguide ID links.

The deterministic matcher never guesses nicknames. A reviewer who has checked a case can record the link here, with
the reason and what they checked. The enrichment service uses an override only for a politician the matcher left
unmatched, and re-validates it against the live official roster every time.

File format (JSON list). A politician is identified by `canonical_key` (stable across databases, unlike the numeric id):
  [{"canonical_key": "house:danielcrenshaw", "politician_name": "Daniel Crenshaw", "bioguide_id": "C001120",
    "reason": "...", "source": "...", "reviewed_at": "2026-10-07"}]
An entry whose politician is not in this database is skipped (and reported); `politician_id` is accepted only for a database-local
file and must agree with `canonical_key` when both are given.
"""

import json
import re
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Politician, PoliticianAliasOverride

BIOGUIDE = re.compile(r"^[A-Z]\d{6}$")


class OverrideError(ValueError):
    """An override that is invalid or conflicts with existing data. Nothing is written."""


def _clean(text: object, field: str, limit: int) -> str:
    value = str(text or "").strip()
    if not value:
        raise OverrideError(f"{field} is required")
    if len(value) > limit:
        raise OverrideError(f"{field} is longer than {limit} characters")
    return value


def validate_override(session: Session, politician_id: int, bioguide_id: str, reason: str, source: str) -> tuple[str, str, str]:
    bioguide = str(bioguide_id or "").strip().upper()
    if not BIOGUIDE.match(bioguide):
        raise OverrideError(f"{bioguide_id!r} is not a Bioguide ID (one letter and six digits)")
    reason, source = _clean(reason, "reason", 500), _clean(source, "source", 200)
    pol = session.get(Politician, politician_id)
    if pol is None:
        raise OverrideError(f"politician #{politician_id} does not exist")
    if pol.enrichment_status == "matched" and not (pol.enrichment_method == "override" and pol.bioguide_id == bioguide):
        raise OverrideError(f"politician #{politician_id} ({pol.name}) is already matched automatically; an override is not needed")
    owner = session.scalar(select(Politician.id).where(Politician.bioguide_id == bioguide, Politician.id != politician_id))
    if owner is not None:
        raise OverrideError(f"{bioguide} is already assigned to politician #{owner}")
    other = session.scalar(
        select(PoliticianAliasOverride.politician_id).where(
            PoliticianAliasOverride.bioguide_id == bioguide, PoliticianAliasOverride.politician_id != politician_id
        )
    )
    if other is not None:
        raise OverrideError(f"{bioguide} is already the override for politician #{other}")
    return bioguide, reason, source


def add_override(session: Session, politician_id: int, bioguide_id: str, reason: str, source: str, reviewed_at: datetime | date | None = None) -> PoliticianAliasOverride:
    bioguide, reason, source = validate_override(session, politician_id, bioguide_id, reason, source)
    when = reviewed_at or datetime.now()
    when = when if isinstance(when, datetime) else datetime.combine(when, datetime.min.time())
    row = session.scalar(select(PoliticianAliasOverride).where(PoliticianAliasOverride.politician_id == politician_id))
    if row is None:
        row = PoliticianAliasOverride(politician_id=politician_id)
        session.add(row)
    row.bioguide_id, row.reason, row.source, row.reviewed_at = bioguide, reason, source, when
    session.flush()
    return row


class LoadResult(list):
    """The override rows recorded, plus `.skipped`: canonical keys in the file that this database does not contain."""

    skipped: list[str]


def load_overrides_file(session: Session, path: Path) -> LoadResult:
    """All or nothing: one invalid entry raises OverrideError and the caller rolls the whole file back."""
    try:
        entries = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise OverrideError(f"cannot read {path}: {exc}") from exc
    if not isinstance(entries, list):
        raise OverrideError("the overrides file must be a JSON list")
    rows = LoadResult()
    rows.skipped = []
    for i, e in enumerate(entries, start=1):
        try:
            reviewed = datetime.fromisoformat(str(e["reviewed_at"]))
            key = e.get("canonical_key")
            if key:
                pol = session.scalar(select(Politician).where(Politician.canonical_key == key))
                if pol is None:
                    rows.skipped.append(key)
                    continue
                if e.get("politician_id") not in (None, pol.id):
                    raise OverrideError(f"politician_id {e['politician_id']} does not belong to {key}")
                pid = pol.id
            elif e.get("politician_id") is not None:
                pid = int(e["politician_id"])
            else:
                raise OverrideError("canonical_key is required")
            rows.append(add_override(session, pid, e["bioguide_id"], e.get("reason"), e.get("source"), reviewed))
        except OverrideError as exc:
            raise OverrideError(f"entry {i}: {exc}") from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise OverrideError(f"entry {i}: {exc}") from exc
    seen: dict[str, int] = {}
    for r in rows:  # two entries in one file may not share an ID either
        if r.bioguide_id in seen and seen[r.bioguide_id] != r.politician_id:
            raise OverrideError(f"{r.bioguide_id} appears for politicians #{seen[r.bioguide_id]} and #{r.politician_id}")
        seen[r.bioguide_id] = r.politician_id
    return rows
