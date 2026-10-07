"""Explicit, human-reviewed politician -> Bioguide ID links.

The deterministic matcher never guesses nicknames. A reviewer who has checked a case can record the link here, with
the reason and what they checked. The enrichment service uses an override only for a politician the matcher left
unmatched, and re-validates it against the live official roster every time.

File format (JSON list):
  [{"politician_id": 45, "bioguide_id": "C001120", "reason": "...", "source": "...", "reviewed_at": "2026-10-07"}]
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


def load_overrides_file(session: Session, path: Path) -> list[PoliticianAliasOverride]:
    """All or nothing: one invalid entry raises OverrideError and the caller rolls the whole file back."""
    try:
        entries = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise OverrideError(f"cannot read {path}: {exc}") from exc
    if not isinstance(entries, list):
        raise OverrideError("the overrides file must be a JSON list")
    rows = []
    for i, e in enumerate(entries, start=1):
        try:
            reviewed = datetime.fromisoformat(str(e["reviewed_at"]))
            rows.append(add_override(session, int(e["politician_id"]), e["bioguide_id"], e.get("reason"), e.get("source"), reviewed))
        except (KeyError, TypeError, ValueError) as exc:
            raise OverrideError(f"entry {i}: {exc}") from exc
    seen: dict[str, int] = {}
    for r in rows:  # two entries in one file may not share an ID either
        if r.bioguide_id in seen and seen[r.bioguide_id] != r.politician_id:
            raise OverrideError(f"{r.bioguide_id} appears for politicians #{seen[r.bioguide_id]} and #{r.politician_id}")
        seen[r.bioguide_id] = r.politician_id
    return rows
