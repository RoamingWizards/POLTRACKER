"""Enrich politicians with official identifiers and committee seats.   python -m poltracker.enrich_politicians

Incremental: politicians already enriched recently, or already tried recently without a match, are skipped without
any API call. Only a verified, unambiguous match is ever written (see politician_match). Unresolved politicians are
recorded with a reason. A missing API key or a provider outage is reported and changes nothing.
"""

import argparse
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .db import make_session_factory
from .models import CommitteeAssignment, Politician, _now
from .politician_match import match_politician
from .providers.base import ProviderError
from .providers.politicians import CommitteeProvider, NotConfigured, PoliticianProvider

log = logging.getLogger(__name__)


@dataclass
class Unresolved:
    politician_id: int
    name: str
    chamber: str
    status: str
    note: str | None


@dataclass
class EnrichmentReport:
    status: str = "ok"  # ok | not_configured | provider_error | nothing_to_do
    message: str = ""
    considered: int = 0
    skipped_current: int = 0
    skipped_recent_attempt: int = 0
    matched: list[tuple[int, str, str]] = field(default_factory=list)  # (id, name, bioguide)
    unresolved: list[Unresolved] = field(default_factory=list)
    committee_seats: int = 0
    committee_message: str = ""
    requests: int = 0
    dry_run: bool = False

    def summary(self) -> str:
        return (
            f"{self.status}: {len(self.matched)} matched, {len(self.unresolved)} unresolved, "
            f"{self.skipped_current} current, {self.skipped_recent_attempt} recently tried, "
            f"{self.committee_seats} committee seats, {self.requests} requests{' (dry run)' if self.dry_run else ''}"
            + (f" | {self.message}" if self.message else "")
        )


def _select(session: Session, now, stale_days, retry_days, force, only_ids, limit, report) -> list[Politician]:
    stmt = select(Politician).order_by(Politician.id)
    if only_ids:
        stmt = stmt.where(Politician.id.in_(only_ids))
    due = []
    for pol in session.scalars(stmt):
        if not force:
            if pol.enrichment_status == "matched" and pol.enriched_at and now - pol.enriched_at < timedelta(days=stale_days):
                report.skipped_current += 1
                continue
            if pol.enrichment_status != "matched" and pol.enrichment_checked_at and now - pol.enrichment_checked_at < timedelta(days=retry_days):
                report.skipped_recent_attempt += 1
                continue
        due.append(pol)
    return due[:limit] if limit else due


def enrich_politicians(
    session_factory: sessionmaker[Session],
    provider: PoliticianProvider,
    committees: CommitteeProvider | None = None,
    *,
    now: datetime | None = None,
    stale_days: int = 30,
    retry_days: int = 7,
    force: bool = False,
    only_ids: set[int] | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> EnrichmentReport:
    now = now or _now()
    report = EnrichmentReport(dry_run=dry_run)
    with session_factory() as session:
        due = _select(session, now, stale_days, retry_days, force, only_ids, limit, report)
        report.considered = len(due)
        if not due:
            report.status, report.message = "nothing_to_do", "every politician is current or was tried recently"
            return report

        try:
            roster = provider.list_members()
        except NotConfigured as exc:
            report.status, report.message = "not_configured", str(exc)
            return report
        except ProviderError as exc:
            report.status, report.message = "provider_error", str(exc)
            return report
        finally:
            report.requests = getattr(provider, "requests_made", 0)

        taken = {
            b: pid for b, pid in session.execute(select(Politician.bioguide_id, Politician.id).where(Politician.bioguide_id.is_not(None)))
        }
        matched_ids: dict[int, str] = {}
        for pol in due:
            result = match_politician(pol.name, pol.chamber, pol.state, roster)
            status, note, member = result.status, result.note, result.member
            if member is not None:
                owner = taken.get(member.bioguide_id)
                if owner is not None and owner != pol.id:
                    status, note, member = "conflict", f"{member.bioguide_id} ({member.full_name}) is already linked to politician #{owner}; not merged", None
                elif pol.bioguide_id and pol.bioguide_id != member.bioguide_id:
                    status, note, member = "conflict", f"already linked to {pol.bioguide_id}; the official match is {member.bioguide_id}; left unchanged", None
            if member is None:
                report.unresolved.append(Unresolved(pol.id, pol.name, pol.chamber, status, note))
                if not dry_run:
                    pol.enrichment_checked_at = now
                    if pol.enrichment_status != "matched":  # never downgrade an earlier verified match
                        pol.enrichment_status, pol.enrichment_note = status, note
                continue
            report.matched.append((pol.id, pol.name, member.bioguide_id))
            taken[member.bioguide_id] = pol.id
            matched_ids[pol.id] = member.bioguide_id
            if not dry_run:
                pol.bioguide_id = member.bioguide_id
                pol.party = member.party or pol.party
                pol.state = member.state or pol.state
                pol.district = member.district
                pol.official_url = member.official_url
                pol.active = member.active
                pol.term_start_year, pol.term_end_year = member.term_start_year, member.term_end_year
                pol.enriched_at = pol.enrichment_checked_at = now
                pol.enrichment_source = member.source or provider.name
                pol.enrichment_status, pol.enrichment_note = "matched", None

        if committees is not None and matched_ids:
            _sync_committees(session, committees, due, matched_ids, report, now, dry_run)
        if not dry_run:
            session.commit()
        else:
            session.rollback()
    return report


def _sync_committees(session, provider: CommitteeProvider, due, matched_ids, report, now, dry_run) -> None:
    wanted = {pid: b for pid, b in matched_ids.items() if next(p for p in due if p.id == pid).chamber in provider.chambers}
    if not wanted:
        return
    try:
        seats = provider.get_committees(set(wanted.values()))
    except ProviderError as exc:  # keep the seats already stored
        report.committee_message = f"committee data unavailable: {exc}"
        return
    finally:
        report.requests += getattr(provider, "requests_made", 0)
    for pid, bioguide in wanted.items():
        mine = seats.get(bioguide, [])
        report.committee_seats += len(mine)
        if dry_run:
            continue
        source = mine[0].source if mine else provider.name
        session.execute(delete(CommitteeAssignment).where(CommitteeAssignment.politician_id == pid, CommitteeAssignment.source == source))
        for seat in mine:
            session.add(
                CommitteeAssignment(
                    politician_id=pid,
                    committee_name=seat.committee_name,
                    committee_code=seat.committee_code,
                    subcommittee_name=seat.subcommittee_name,
                    subcommittee_code=seat.subcommittee_code,
                    role=seat.role,
                    chamber=seat.chamber,
                    start_date=seat.start_date,
                    end_date=seat.end_date,
                    source=seat.source,
                    source_url=seat.source_url,
                    fetched_at=now,
                )
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enrich politicians with official identifiers and committee seats")
    parser.add_argument("--source", choices=["congress.gov", "house-clerk"], default="congress.gov",
                        help="roster to match against (house-clerk: House members only, no API key needed)")
    parser.add_argument("--limit", type=int, help="enrich at most this many politicians")
    parser.add_argument("--ids", type=int, nargs="+", help="only these politician ids")
    parser.add_argument("--force", action="store_true", help="ignore the recency rules")
    parser.add_argument("--dry-run", action="store_true", help="match and report, write nothing")
    parser.add_argument("--no-committees", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    from .providers.congress_gov import CongressGovProvider
    from .providers.house_clerk import HouseClerkProvider

    clerk = HouseClerkProvider()
    provider = clerk if args.source == "house-clerk" else CongressGovProvider(
        settings.congress_api_key, base_url=settings.congress_api_base_url, congress=settings.congress_number,
        min_interval=settings.politician_request_interval,
    )
    report = enrich_politicians(
        make_session_factory(), provider, None if args.no_committees else clerk,
        stale_days=settings.politician_enrich_stale_days, retry_days=settings.politician_retry_days,
        force=args.force, only_ids=set(args.ids) if args.ids else None, limit=args.limit, dry_run=args.dry_run,
    )
    print(report.summary())
    for pid, name, bioguide in report.matched:
        print(f"  matched    #{pid:<4} {name:<28} {bioguide}")
    for u in report.unresolved:
        print(f"  {u.status:<10} #{u.politician_id:<4} {u.name:<28} {u.note}")
    if report.committee_message:
        print(f"  committees: {report.committee_message}")
    return {"ok": 0, "nothing_to_do": 0, "not_configured": 2, "provider_error": 1}[report.status]


if __name__ == "__main__":
    raise SystemExit(main())
