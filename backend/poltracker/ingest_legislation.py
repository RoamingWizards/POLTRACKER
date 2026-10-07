"""Ingest bounded legislative data from Congress.gov.   python -m poltracker.ingest_legislation

Stores bills (with summaries, subjects, committees, sponsor/cosponsor links and in-window actions) and hearings for a date window.
It does NOT score, flag or contextualize trades, and never touches trades, securities, prices or politicians.

Scope: a bill is stored when it has an official action dated inside [from, to]; a hearing when it has a date inside the window.
Incremental: a bill whose Congress.gov updateDate is unchanged (and not today's) is skipped without any further request.
Safe to re-run: every child row has a unique key, and children are synced to the latest official data.
"""

import argparse
import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .db import make_session_factory
from .models import (
    BillAction, Hearing, HearingCommittee, Legislation, LegislationCommittee, LegislationSubject, Politician, PoliticianLegislation, Trade, _now,
)
from .providers.base import ProviderError, ProviderRateLimited
from .providers.legislation import Bill, BillRef, LegislationProvider, congress_for, congress_start
from .providers.politicians import NotConfigured

log = logging.getLogger(__name__)


@dataclass
class LegislationReport:
    status: str = "ok"  # ok | not_configured | rate_limited | provider_error
    message: str = ""
    from_date: date | None = None
    to_date: date | None = None
    dry_run: bool = False
    bills_listed: int = 0
    bills_before_window: int = 0  # latest action older than the window: cannot have an action inside it
    bills_unchanged: int = 0
    bills_out_of_scope: int = 0  # no official action inside the window
    bills_fetched: int = 0  # in scope and fully read
    bills_inserted: int = 0
    bills_updated: int = 0
    subjects_inserted: int = 0
    committees_inserted: int = 0
    actions_inserted: int = 0
    links_inserted: int = 0  # sponsor / cosponsor links to existing POLTRACKER politicians
    sponsors_not_in_poltracker: int = 0
    hearings_listed: int = 0
    hearings_unchanged: int = 0
    hearings_out_of_scope: int = 0
    hearings_inserted: int = 0
    hearings_updated: int = 0
    requests: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        n = lambda v: f"{v:,}"  # noqa: E731
        lines = [
            f"Window: {self.from_date} to {self.to_date}{' (dry run: nothing written)' if self.dry_run else ''}",
            f"Bills listed: {n(self.bills_listed)} (before window: {n(self.bills_before_window)}, unchanged: {n(self.bills_unchanged)}, "
            f"no action in window: {n(self.bills_out_of_scope)})",
            f"Bills fetched: {n(self.bills_fetched)}  inserted: {n(self.bills_inserted)}  updated: {n(self.bills_updated)}",
            f"Subjects: {n(self.subjects_inserted)}  Committees: {n(self.committees_inserted)}  Actions: {n(self.actions_inserted)}  "
            f"Sponsor/cosponsor links: {n(self.links_inserted)}",
            f"Hearings listed: {n(self.hearings_listed)} (unchanged: {n(self.hearings_unchanged)}, outside window: {n(self.hearings_out_of_scope)})  "
            f"inserted: {n(self.hearings_inserted)}  updated: {n(self.hearings_updated)}",
            f"Requests made: {n(self.requests)}",
            f"Errors: {len(self.errors)}",
        ]
        if self.message:
            lines.insert(0, f"{self.status}: {self.message}")
        return "\n".join(lines)


def default_window(session_factory: sessionmaker[Session], today: date, buffer_days: int = 30) -> tuple[date, date]:
    """From the later of (earliest valid trade date minus a buffer) and the start of the current Congress, to today.

    The current-Congress floor keeps ingestion to one Congress. With no trades the window is the last 365 days.
    """
    with session_factory() as session:
        earliest = session.scalar(select(func.min(Trade.transaction_date)).where(Trade.transaction_date <= today))
    floor = congress_start(congress_for(today))
    if earliest is None:
        return max(today - timedelta(days=365), floor), today
    return max(earliest - timedelta(days=buffer_days), floor), today


def action_key(when: date, code: str | None, text: str) -> str:
    return hashlib.sha1(f"{when.isoformat()}|{code or ''}|{text}".encode()).hexdigest()


def _sync_subjects(session, leg: Legislation, subjects: list[str], report) -> None:
    subjects = list(dict.fromkeys(n.strip() for n in subjects if n and n.strip()))  # the source may repeat a subject
    have = {s.subject: s for s in leg.subjects}
    for name, row in have.items():
        if name not in subjects:
            leg.subjects.remove(row)
    for name in subjects:
        if name not in have:
            leg.subjects.append(LegislationSubject(subject=name[:300]))
            report.subjects_inserted += 1


def _sync_committees(session, leg: Legislation, committees, report) -> None:
    want = {c.code: c for c in committees}
    have = {c.committee_code: c for c in leg.committees}
    for code, row in have.items():
        if code not in want:
            leg.committees.remove(row)
        else:
            row.committee_name, row.chamber = want[code].name[:300], want[code].chamber
    for code, c in want.items():
        if code not in have:
            leg.committees.append(LegislationCommittee(committee_code=code[:20], committee_name=c.name[:300], chamber=c.chamber))
            report.committees_inserted += 1


def _sync_actions(session, leg: Legislation, actions, report) -> None:
    have = {a.action_key for a in leg.actions}
    for a in actions:
        key = action_key(a.action_date, a.code, a.text)
        if key not in have:
            have.add(key)
            leg.actions.append(BillAction(action_date=a.action_date, action_text=a.text, action_code=a.code, action_type=a.action_type, action_key=key))
            report.actions_inserted += 1


def _sync_links(session, leg: Legislation, bill: Bill, cosponsors, bio_map: dict[str, int], report) -> None:
    """Sponsor / cosponsor links only for existing politicians, matched by Bioguide ID. No name matching, nothing created."""
    want: dict[tuple[int, str], dict] = {}
    if bill.sponsor:
        if bill.sponsor.bioguide_id in bio_map:
            want[(bio_map[bill.sponsor.bioguide_id], "sponsor")] = {"date": bill.introduced_date, "original": None, "withdrawn": None}
        else:
            report.sponsors_not_in_poltracker += 1
    for c in cosponsors:
        if c.bioguide_id in bio_map:
            want[(bio_map[c.bioguide_id], "cosponsor")] = {"date": c.sponsorship_date, "original": c.original, "withdrawn": c.withdrawn_date}
    have = {(l.politician_id, l.relationship_type): l for l in leg.politician_links}
    for key, row in have.items():
        if key not in want:
            leg.politician_links.remove(row)
        else:
            w = want[key]
            row.sponsorship_date, row.is_original, row.withdrawn_date = w["date"], w["original"], w["withdrawn"]
    for (pid, rel), w in want.items():
        if (pid, rel) not in have:
            leg.politician_links.append(
                PoliticianLegislation(politician_id=pid, relationship_type=rel, sponsorship_date=w["date"], is_original=w["original"], withdrawn_date=w["withdrawn"])
            )
            report.links_inserted += 1


def _write_bill(session, ref: BillRef, bill: Bill, actions, policy_area, subjects, summaries, cosponsors, committees, bio_map, report) -> None:
    leg = session.scalar(select(Legislation).where(Legislation.congress == ref.congress, Legislation.bill_type == ref.bill_type, Legislation.bill_number == ref.number))
    if leg is None:
        leg = Legislation(congress=ref.congress, bill_type=ref.bill_type, bill_number=ref.number)
        session.add(leg)
        report.bills_inserted += 1
    else:
        report.bills_updated += 1
    leg.title = bill.ref.title or ref.title
    leg.origin_chamber = bill.origin_chamber
    leg.introduced_date = bill.introduced_date
    leg.latest_action_date, leg.latest_action_text = bill.ref.latest_action_date or ref.latest_action_date, bill.ref.latest_action_text or ref.latest_action_text
    leg.policy_area = (policy_area or bill.policy_area or "")[:200] or None
    leg.sponsor_bioguide_id = bill.sponsor.bioguide_id if bill.sponsor else None
    leg.sponsor_name = (bill.sponsor.full_name or "")[:200] or None if bill.sponsor else None
    leg.cosponsor_count = len(cosponsors) if cosponsors is not None else bill.cosponsors_count
    leg.source_url = bill.source_url
    leg.api_update_date = ref.update_date
    if summaries:  # the most recent official summary; the text is stored as published, with markup removed
        latest = max(summaries, key=lambda s: (s.action_date or date.min, s.update_date or datetime.min))
        leg.summary, leg.summary_date = latest.text, latest.action_date
    leg.updated_at = _now()
    session.flush()
    _sync_subjects(session, leg, subjects, report)
    _sync_committees(session, leg, committees, report)
    _sync_actions(session, leg, actions, report)
    _sync_links(session, leg, bill, cosponsors, bio_map, report)


def _ingest_bills(session_factory, provider, report, from_date, to_date, today, force, limit, bio_map) -> None:
    session = session_factory()
    considered = 0
    try:
        for congress in range(congress_for(from_date), congress_for(to_date) + 1):
            for ref in provider.list_bills(congress, from_date=from_date):
                report.bills_listed += 1
                if ref.latest_action_date is None or ref.latest_action_date < from_date:
                    report.bills_before_window += 1
                    continue
                if limit is not None and considered >= limit:
                    return
                considered += 1
                existing = session.scalar(select(Legislation.api_update_date).where(
                    Legislation.congress == ref.congress, Legislation.bill_type == ref.bill_type, Legislation.bill_number == ref.number))
                if not force and existing is not None and ref.update_date is not None and existing == ref.update_date and ref.update_date < today:
                    report.bills_unchanged += 1
                    continue
                try:  # reading only: nothing has been written for this bill yet, so a failure cannot affect earlier bills
                    actions = [a for a in provider.get_bill_actions(ref) if from_date <= a.action_date <= to_date]
                    if not actions:  # cheapest scope test first: one request decides whether the rest is needed
                        report.bills_out_of_scope += 1
                        continue
                    bill = provider.get_bill(ref)
                    if bill is None:
                        report.errors.append(f"{ref.bill_type.upper()}{ref.number}/{ref.congress}: bill record not found")
                        continue
                    policy, subjects = provider.get_bill_subjects(ref) if bill.subjects_count else (bill.policy_area, [])
                    summaries = provider.get_bill_summaries(ref) if bill.summaries_count else []
                    cosponsors = provider.get_bill_cosponsors(ref) if bill.cosponsors_count else []
                    committees = provider.get_bill_committees(ref) if bill.committees_count else []
                except ProviderRateLimited:
                    raise
                except ProviderError as exc:
                    report.errors.append(f"{ref.bill_type.upper()}{ref.number}/{ref.congress}: {exc}")
                    continue
                counters = (report.bills_inserted, report.bills_updated, report.subjects_inserted, report.committees_inserted,
                            report.actions_inserted, report.links_inserted, report.sponsors_not_in_poltracker)
                try:  # one bill per transaction: a failure loses only that bill, and a dry run can roll everything back
                    _write_bill(session, ref, bill, actions, policy, subjects, summaries, cosponsors, committees, bio_map, report)
                    session.rollback() if report.dry_run else session.commit()
                except Exception as exc:  # noqa: BLE001 - keep ingesting; the bill is reported
                    session.rollback()
                    (report.bills_inserted, report.bills_updated, report.subjects_inserted, report.committees_inserted,
                     report.actions_inserted, report.links_inserted, report.sponsors_not_in_poltracker) = counters
                    report.errors.append(f"{ref.bill_type.upper()}{ref.number}/{ref.congress}: could not be saved ({type(exc).__name__})")
                    continue
                report.bills_fetched += 1
    finally:
        try:
            session.rollback() if report.dry_run else session.commit()
        finally:
            session.close()


def _ingest_hearings(session_factory, provider, report, from_date, to_date, today, force, limit) -> None:
    session = session_factory()
    considered = 0
    try:
        for congress in range(congress_for(from_date), congress_for(to_date) + 1):
            for ref in provider.list_hearings(congress):
                report.hearings_listed += 1
                if limit is not None and considered >= limit:
                    return
                considered += 1
                row = session.scalar(select(Hearing).where(Hearing.congress == ref.congress, Hearing.chamber == ref.chamber, Hearing.jacket_number == ref.jacket_number))
                if not force and row is not None and ref.update_date is not None and row.api_update_date == ref.update_date and ref.update_date.date() < today:
                    report.hearings_unchanged += 1
                    continue
                try:
                    hearing = provider.get_hearing(ref)
                except ProviderRateLimited:
                    raise
                except ProviderError as exc:
                    report.errors.append(f"hearing {ref.chamber}/{ref.jacket_number}: {exc}")
                    continue
                if hearing is None or not any(from_date <= d <= to_date for d in hearing.dates):
                    report.hearings_out_of_scope += 1
                    continue
                if row is None:
                    row = Hearing(congress=ref.congress, chamber=ref.chamber, jacket_number=ref.jacket_number)
                    session.add(row)
                    report.hearings_inserted += 1
                else:
                    report.hearings_updated += 1
                row.title, row.citation, row.event_id, row.source_url = hearing.title, hearing.citation, hearing.event_id, hearing.source_url
                row.hearing_date, row.hearing_end_date = hearing.dates[0], hearing.dates[-1] if len(hearing.dates) > 1 else None
                row.api_update_date = ref.update_date
                row.updated_at = _now()
                session.flush()
                want = {c.code: c for c in hearing.committees}
                have = {c.committee_code: c for c in row.committees}
                for code, c in have.items():
                    if code not in want:
                        row.committees.remove(c)
                for code, c in want.items():
                    if code not in have:
                        row.committees.append(HearingCommittee(committee_code=code[:20], committee_name=c.name[:300]))
                session.rollback() if report.dry_run else session.commit()
    finally:
        try:
            session.rollback() if report.dry_run else session.commit()
        finally:
            session.close()


def ingest_legislation(
    session_factory: sessionmaker[Session],
    provider: LegislationProvider,
    *,
    from_date: date,
    to_date: date,
    dry_run: bool = False,
    force: bool = False,
    limit: int | None = None,
    hearings: bool = True,
    today: date | None = None,
) -> LegislationReport:
    today = today or date.today()
    report = LegislationReport(from_date=from_date, to_date=to_date, dry_run=dry_run)
    if from_date > to_date:
        report.status, report.message = "provider_error", "from-date is after to-date"
        return report
    with session_factory() as session:
        bio_map = {b: i for b, i in session.execute(select(Politician.bioguide_id, Politician.id).where(Politician.bioguide_id.is_not(None)))}
    try:
        _ingest_bills(session_factory, provider, report, from_date, to_date, today, force, limit, bio_map)
        if hearings:
            _ingest_hearings(session_factory, provider, report, from_date, to_date, today, force, limit)
    except NotConfigured as exc:
        report.status, report.message = "not_configured", str(exc)
    except ProviderRateLimited as exc:
        report.status, report.message = "rate_limited", f"stopped early ({exc}); progress so far is saved, re-run to continue"
    except ProviderError as exc:
        report.status, report.message = "provider_error", str(exc)
    finally:
        report.requests = getattr(provider, "requests_made", 0)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest bounded legislative data from Congress.gov (needs CONGRESS_API_KEY)")
    parser.add_argument("--from-date", type=date.fromisoformat, help="window start (default: see docs; usually the start of the current Congress)")
    parser.add_argument("--to-date", type=date.fromisoformat, help="window end (default: today)")
    parser.add_argument("--dry-run", action="store_true", help="read from Congress.gov and report what would change; write nothing")
    parser.add_argument("--force", action="store_true", help="re-read bills and hearings even if Congress.gov reports no change")
    parser.add_argument("--limit", type=int, help="consider at most this many bills and this many hearings")
    parser.add_argument("--no-hearings", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    from .providers.congress_gov import CongressGovProvider

    provider = CongressGovProvider(
        settings.congress_api_key, base_url=settings.congress_api_base_url, congress=settings.congress_number,
        min_interval=settings.politician_request_interval,
    )
    factory = make_session_factory()
    today = date.today()
    default_from, default_to = default_window(factory, today, settings.legislation_buffer_days)
    report = ingest_legislation(
        factory, provider, from_date=args.from_date or default_from, to_date=args.to_date or default_to,
        dry_run=args.dry_run, force=args.force, limit=args.limit, hearings=not args.no_hearings, today=today,
    )
    print(report.summary())
    for e in report.errors[:10]:
        print(f"  error: {e}")
    if len(report.errors) > 10:
        print(f"  ... and {len(report.errors) - 10} more")
    return {"ok": 0, "not_configured": 2, "rate_limited": 3, "provider_error": 1}[report.status]


if __name__ == "__main__":
    raise SystemExit(main())
