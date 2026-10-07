"""Committee seat history from adopted House resolutions.   python -m poltracker.enrich_committee_history

Fetches the engrossed House resolutions of a Congress from govinfo (2 bulk downloads, cached), reads the committee elections and removals in them, and writes
dated committee seats for the politicians in scope. It also records the House Clerk snapshot's own provenance (Congress and publish date) on the seats it already
has. It touches only committee_assignments. Nothing is inferred: see committee_history.py for exactly what a record does and does not establish.
"""

import argparse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, sessionmaker

from .committee_history import (
    PRECISION_EXACT, PRECISION_SNAPSHOT, SOURCE, SOURCE_TYPE, Roster, build_events, build_intervals, parse_roster,
)
from .db import make_session_factory
from .models import CommitteeAssignment, Politician, Trade, TradeContext
from .providers.base import ProviderError
from .providers.house_resolutions import HouseResolutionsProvider

CLERK_URL = "https://clerk.house.gov/xml/lists/MemberData.xml"


@dataclass
class HistoryReport:
    congress: int
    resolutions: int = 0
    events: int = 0
    unresolved_names: int = 0
    ambiguous_names: int = 0
    unmapped_committees: list[str] = field(default_factory=list)
    politicians_in_scope: int = 0
    politicians_with_history: int = 0
    intervals_written: int = 0
    incomplete_intervals: int = 0
    snapshot_rows_annotated: int = 0
    requests: int = 0
    dry_run: bool = False

    def to_text(self) -> str:
        n = lambda v: f"{v:,}"  # noqa: E731
        return "\n".join([
            f"Congress {self.congress}: {n(self.resolutions)} committee resolutions read, {n(self.events)} elections/removals placed on a member"
            + (" (dry run: nothing written)" if self.dry_run else ""),
            f"  names set aside: {n(self.unresolved_names)} matching no roster member, {n(self.ambiguous_names)} that could be more than one member",
            f"  politicians in scope {n(self.politicians_in_scope)}, with dated committee history {n(self.politicians_with_history)}",
            f"  dated seats written {n(self.intervals_written)} ({n(self.incomplete_intervals)} marked history-incomplete)",
            f"  Clerk snapshot seats annotated with their provenance: {n(self.snapshot_rows_annotated)}",
            f"  network requests: {n(self.requests)}" + (f"; committee headings not matched: {', '.join(self.unmapped_committees)}" if self.unmapped_committees else ""),
        ])


def politicians_in_scope(session: Session, scope: str, ids: list[int] | None) -> dict[int, str]:
    """politician id -> Bioguide ID for the politicians whose history is wanted."""
    stmt = select(Politician.id, Politician.bioguide_id).where(Politician.bioguide_id.is_not(None))
    if ids:
        stmt = stmt.where(Politician.id.in_(ids))
    elif scope == "committee-relevant":
        # Anyone who has had a committee-relevant trade under ANY stored context version (an earlier run is the baseline this history is meant to check).
        stmt = stmt.where(Politician.id.in_(
            select(Trade.politician_id).join(TradeContext, TradeContext.trade_id == Trade.id).where(TradeContext.committee_relevance.is_(True))))
    return {pid: bio for pid, bio in session.execute(stmt).all()}


def sync_history(factory: sessionmaker[Session], roster: Roster, documents: list[tuple[str, str, bytes]], congress: int, *, scope: str = "committee-relevant",
                 ids: list[int] | None = None, dry_run: bool = False, now: datetime | None = None) -> HistoryReport:
    now = now or datetime.now(UTC).replace(tzinfo=None)
    report = HistoryReport(congress, dry_run=dry_run)
    docs = [d for d in documents if f"BILLS-{congress}hres" in d[1]]
    events, parsed = build_events(docs, roster)
    report.resolutions, report.events = parsed.resolutions, parsed.events
    report.unresolved_names, report.ambiguous_names = parsed.unresolved_names, parsed.ambiguous_names
    report.unmapped_committees = sorted(h for h in parsed.unmapped_committees if h.startswith("Committee on"))
    intervals = build_intervals(events, roster, parsed.ambiguous_members)
    by_member: dict[str, list] = {}
    for i in intervals:
        by_member.setdefault(i.bioguide_id, []).append(i)
    with factory() as session:
        scoped = politicians_in_scope(session, scope, ids)
        report.politicians_in_scope = len(scoped)
        for pid, bio in scoped.items():
            mine = by_member.get(bio, [])
            if mine:
                report.politicians_with_history += 1
            report.intervals_written += len(mine)
            report.incomplete_intervals += sum(1 for i in mine if not i.history_complete)
            if dry_run:
                continue
            session.execute(delete(CommitteeAssignment).where(CommitteeAssignment.politician_id == pid, CommitteeAssignment.source == SOURCE,
                                                              CommitteeAssignment.congress_number == congress))
            for i in mine:
                session.add(CommitteeAssignment(
                    politician_id=pid, committee_name=roster.committees[i.committee_code], committee_code=i.committee_code, subcommittee_name=None, subcommittee_code="",
                    role="Member", chamber="house", start_date=i.start, end_date=i.end, source=SOURCE, source_url=i.url, fetched_at=now, congress_number=congress,
                    temporal_precision=PRECISION_EXACT, source_type=SOURCE_TYPE, verified_at=now, verified_through=i.verified_through, history_complete=i.history_complete,
                ))
        if not dry_run and roster.snapshot_date:  # the snapshot's own provenance: a point in time in a Congress, never a seat start date
            result = session.execute(
                update(CommitteeAssignment).where(CommitteeAssignment.source == "house.clerk", CommitteeAssignment.temporal_precision.in_([PRECISION_SNAPSHOT]))
                .values(congress_number=roster.congress_number, verified_through=roster.snapshot_date, verified_at=now))
            report.snapshot_rows_annotated = result.rowcount or 0
        if dry_run:
            session.rollback()
        else:
            session.commit()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Committee seat history from adopted House resolutions (govinfo); writes only committee_assignments")
    parser.add_argument("--congress", type=int, default=119)
    parser.add_argument("--scope", choices=["committee-relevant", "all"], default="committee-relevant",
                        help="whose history to store: politicians with committee-relevant trades (default), or everyone with a Bioguide ID")
    parser.add_argument("--politician-ids", type=int, nargs="+")
    parser.add_argument("--clerk-xml", type=Path, help="use this saved MemberData.xml instead of downloading it")
    parser.add_argument("--cache-dir", type=Path, help="keep the govinfo zips here so a rerun makes no request")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    provider = HouseResolutionsProvider(cache_dir=args.cache_dir)
    requests = 0
    try:
        if args.clerk_xml:
            root = ET.parse(args.clerk_xml).getroot()
        else:
            requests += 1
            resp = httpx.get(CLERK_URL, timeout=60, follow_redirects=True, headers={"User-Agent": "POLTRACKER/0.1"})
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
        roster = parse_roster(root)
        documents = provider.engrossed_documents(args.congress)
    except (ProviderError, httpx.HTTPError, ET.ParseError) as exc:
        print(f"Cannot build committee history: {exc}")
        return 1
    report = sync_history(make_session_factory(), roster, documents, args.congress, scope=args.scope, ids=args.politician_ids, dry_run=args.dry_run)
    report.requests = requests + provider.requests_made
    print(report.to_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
