"""Enrich politicians with official identifiers and committee seats.   python -m poltracker.enrich_politicians

Incremental: politicians already enriched recently, or already tried recently without a match, are skipped without
any API call. Only a verified, unambiguous match is ever written (see politician_match). Unresolved politicians are
recorded with a reason. A missing API key or a provider outage is reported and changes nothing.
"""

import argparse
import logging
import os
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .db import make_session_factory
from .models import CommitteeAssignment, Politician, PoliticianAliasOverride, PoliticianLlmSuggestion, _now
from .politician_llm import IdentityRequest, IdentityResolver, LLMError, LLMSuggestion, cache_key, valid_candidates, validate_suggestion
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
    overrides_applied: list[tuple[int, str, str]] = field(default_factory=list)  # (id, name, bioguide)
    warnings: list[str] = field(default_factory=list)
    llm_calls: int = 0
    llm_cached: int = 0
    llm_resolved: list[tuple[int, str, str]] = field(default_factory=list)  # (id, name, bioguide): applied (auto-accept only)
    llm_pending_review: list[tuple[int, str, str]] = field(default_factory=list)  # validated, held for a person to approve
    llm_errors: list[str] = field(default_factory=list)
    llm_trace: list[dict] = field(default_factory=list)  # one entry per politician the model was asked about (or served from cache)
    requests: int = 0
    dry_run: bool = False

    def summary(self) -> str:
        return (
            f"{self.status}: {len(self.matched)} matched, {len(self.unresolved)} unresolved, "
            f"{self.skipped_current} current, {self.skipped_recent_attempt} recently tried, "
            f"{self.committee_seats} committee seats, {self.requests} requests{' (dry run)' if self.dry_run else ''}"
            + (f" | {self.message}" if self.message else "")
        )


def _select(session: Session, now, stale_days, retry_days, force, only_ids, limit, report, overrides, llm_pending=frozenset()) -> list[Politician]:
    stmt = select(Politician).order_by(Politician.id)
    if only_ids:
        stmt = stmt.where(Politician.id.in_(only_ids))
    due = []
    for pol in session.scalars(stmt):
        if pol.id in overrides and pol.enrichment_status != "matched":
            due.append(pol)  # a reviewed override is applied on the next run, not after the retry window
            continue
        if pol.id in llm_pending and pol.enrichment_status == "unmatched":
            due.append(pol)  # an explicit LLM run reaches unmatched politicians the model has not seen yet
            continue
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
    llm: IdentityResolver | None = None,
    llm_min_confidence: float = 0.9,
    llm_max_calls: int = 25,
    llm_auto_accept: bool = False,
) -> EnrichmentReport:
    now = now or _now()
    report = EnrichmentReport(dry_run=dry_run)
    with session_factory() as session:
        overrides = {o.politician_id: o for o in session.scalars(select(PoliticianAliasOverride))}
        llm_pending = frozenset()
        if llm is not None:
            seen = set(session.scalars(select(PoliticianLlmSuggestion.politician_id).where(PoliticianLlmSuggestion.politician_id.is_not(None))))
            llm_pending = frozenset(set(session.scalars(select(Politician.id))) - seen)
        due = _select(session, now, stale_days, retry_days, force, only_ids, limit, report, overrides, llm_pending)
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

        roster_by_id = {m.bioguide_id: m for m in roster}
        taken = {
            b: pid for b, pid in session.execute(select(Politician.bioguide_id, Politician.id).where(Politician.bioguide_id.is_not(None)))
        }
        matched_ids: dict[int, str] = {}
        for pol in due:
            result = match_politician(pol.name, pol.chamber, pol.state, roster)  # the deterministic matcher always runs first
            status, note, member, method = result.status, result.note, result.member, result.rule
            override = overrides.get(pol.id)
            by_override = by_llm = False
            if override is not None and status == "unmatched":  # only for records the matcher could not resolve
                status, note, member = _resolve_override(pol, override, roster_by_id)
                by_override = member is not None
                method = "override" if by_override else None
            elif override is not None and member is not None and member.bioguide_id != override.bioguide_id:
                report.warnings.append(
                    f"#{pol.id} {pol.name}: override {override.bioguide_id} ignored; the automatic match {member.bioguide_id} was kept"
                )
            if member is None and status == "unmatched" and llm is not None:
                # Last automated step, after the matcher and any reviewed override. Never for resolved politicians.
                member, llm_note, held = _llm_stage(
                    session, pol, result.candidates, roster_by_id, taken, llm, llm_min_confidence, llm_max_calls, llm_auto_accept,
                    report, now, dry_run,
                )
                by_llm = member is not None
                method = "llm" if by_llm else None
                if held:  # validated, but a person must approve it: nothing is assigned
                    status = "review"
                if member is None and llm_note:
                    note = f"{note or ''} | {llm_note}"[:500]
                elif by_llm:
                    status, note = "matched", llm_note
            if member is not None:
                owner = taken.get(member.bioguide_id)
                if owner is not None and owner != pol.id:
                    status, note, member = "conflict", f"{member.bioguide_id} ({member.full_name}) is already linked to politician #{owner}; not merged", None
                    by_override = by_llm = False
                elif pol.bioguide_id and pol.bioguide_id != member.bioguide_id:
                    status, note, member = "conflict", f"already linked to {pol.bioguide_id}; the official match is {member.bioguide_id}; left unchanged", None
                    by_override = by_llm = False
            if member is None:
                report.unresolved.append(Unresolved(pol.id, pol.name, pol.chamber, status, note))
                if not dry_run:
                    pol.enrichment_checked_at = now
                    if pol.enrichment_status != "matched":  # never downgrade an earlier verified match
                        pol.enrichment_status, pol.enrichment_note = status, note
                continue
            report.matched.append((pol.id, pol.name, member.bioguide_id))
            if by_override:
                report.overrides_applied.append((pol.id, pol.name, member.bioguide_id))
            if by_llm:
                report.llm_resolved.append((pol.id, pol.name, member.bioguide_id))
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
                pol.enrichment_status, pol.enrichment_method = "matched", method
                pol.enrichment_note = (
                    f"Reviewed override: {override.reason} (source: {override.source}; reviewed {override.reviewed_at:%Y-%m-%d})"[:500]
                    if by_override else (note if by_llm else None)
                )

        if committees is not None and matched_ids:
            _sync_committees(session, committees, due, matched_ids, report, now, dry_run)
        if not dry_run:
            session.commit()
        else:
            session.rollback()
    return report


def _llm_stage(session, pol, candidates, roster_by_id, taken, llm, min_confidence, max_calls, auto_accept, report, now, dry_run):
    """Ask the model about one unresolved politician. Returns (member or None, note, held_for_review).

    Every suggestion is validated deterministically. Unless auto_accept is on, even a validated suggestion is only
    recorded and held for a person to approve; nothing is assigned to the politician.
    """
    request = IdentityRequest(pol.name, pol.chamber, pol.state, pol.district, tuple(candidates))
    if not request.candidates:
        return None, "LLM not consulted: no same-surname official in the chamber", False
    valid = valid_candidates(request)
    if len(valid) != 1:  # nothing to choose between, or too many to choose safely: no call, straight to review
        return None, f"LLM not consulted: {len(valid)} valid candidates", False
    key = cache_key(request, llm.model)
    row = session.scalar(select(PoliticianLlmSuggestion).where(PoliticianLlmSuggestion.cache_key == key))
    from_cache = row is not None
    if row is not None:  # the same unresolved name is never sent twice
        report.llm_cached += 1
        suggestion = LLMSuggestion(
            row.selected_bioguide_id, row.confidence, row.explanation or "",
            tuple(a for a in (row.alternates or "").split(",") if a), row.model,
        )
    else:
        if report.llm_calls >= max_calls:
            return None, "LLM not consulted: per-run call limit reached", False
        try:
            suggestion = llm.resolve(request)
        except LLMError as exc:
            report.llm_errors.append(f"#{pol.id} {pol.name}: {exc}")
            return None, "LLM unavailable", False  # not cached, so it is retried later
        report.llm_calls += 1
        if not dry_run:
            row = PoliticianLlmSuggestion(
                cache_key=key, incoming_name=pol.name, chamber=pol.chamber, model=suggestion.model or llm.model,
                candidate_ids=",".join(sorted(m.bioguide_id for m in request.candidates))[:2000],
                selected_bioguide_id=suggestion.selected_bioguide_id, confidence=suggestion.confidence,
                explanation=suggestion.explanation, alternates=",".join(suggestion.alternate_candidates)[:500], created_at=now,
            )
            session.add(row)
    verdict = validate_suggestion(suggestion, request, roster_by_id, taken, pol.id, min_confidence)
    held = verdict.member is not None and not auto_accept
    if row is not None and not dry_run:
        row.politician_id = pol.id
        row.outcome = "rejected" if verdict.member is None else ("review" if held else "accepted")
        row.reason = None if verdict.member else (verdict.reason or "")[:300]
        row.decided_at = now
    report.llm_trace.append({
        "id": pol.id, "name": pol.name, "chamber": pol.chamber, "candidates": [(m.full_name, m.bioguide_id, m.state) for m in request.candidates],
        "selected": suggestion.selected_bioguide_id, "confidence": suggestion.confidence, "explanation": suggestion.explanation,
        "alternates": list(suggestion.alternate_candidates), "accepted": verdict.member is not None, "held_for_review": held,
        "reason": verdict.reason, "cached": from_cache,
    })
    if verdict.member is None:
        return None, f"LLM suggestion rejected: {verdict.reason}", False
    if held:
        report.llm_pending_review.append((pol.id, pol.name, verdict.member.bioguide_id))
        # The explanation is model output, not evidence; it is recorded in the audit table, not in this note.
        return None, (
            f"LLM suggests {verdict.member.bioguide_id} ({verdict.member.full_name}), confidence {suggestion.confidence:.2f}; "
            "validated, awaiting review. Approve it as a reviewed override to apply it"
        ), True
    return verdict.member, (
        f"LLM-assisted ({suggestion.model or llm.model}, confidence {suggestion.confidence:.2f}): {suggestion.explanation}"
    ), False


def review_queue(session_factory: sessionmaker[Session]) -> list[dict]:
    """Politicians still unresolved, with the latest LLM outcome if one was recorded."""
    with session_factory() as session:
        out = []
        for pol in session.scalars(select(Politician).where(Politician.enrichment_status.is_not(None), Politician.enrichment_status != "matched").order_by(Politician.id)):
            llm = session.scalar(
                select(PoliticianLlmSuggestion).where(PoliticianLlmSuggestion.politician_id == pol.id).order_by(PoliticianLlmSuggestion.id.desc())
            )
            out.append({
                "id": pol.id, "name": pol.name, "chamber": pol.chamber, "status": pol.enrichment_status, "note": pol.enrichment_note,
                "llm_selected": llm.selected_bioguide_id if llm else None, "llm_confidence": llm.confidence if llm else None,
                "llm_outcome": llm.outcome if llm else None, "llm_reason": llm.reason if llm else None,
            })
        return out


def _resolve_override(pol: Politician, override: PoliticianAliasOverride, roster_by_id: dict) -> tuple[str, str | None, object]:
    """Check a reviewed override against the live official roster. Anything off fails safely as a 'conflict'."""
    member = roster_by_id.get(override.bioguide_id)
    if member is None:
        return "conflict", f"override {override.bioguide_id} is not in the official roster; not applied", None
    if member.chamber != pol.chamber:
        return "conflict", f"override {override.bioguide_id} is a {member.chamber} member but this politician is in the {pol.chamber}; not applied", None
    if pol.state and member.state and member.state != pol.state:
        return "conflict", f"override {override.bioguide_id} is from {member.state} but this politician is recorded as {pol.state}; not applied", None
    return "matched", None, member


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
    parser.add_argument("--llm", action="store_true", help="after the deterministic steps, ask the LLM about unmatched politicians (needs OPENAI_API_KEY)")
    parser.add_argument("--review-queue", action="store_true", help="list unresolved politicians and any LLM outcome, then exit")
    parser.add_argument("--overrides", type=Path, help="JSON file of reviewed politician -> Bioguide ID overrides to record first")
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
    factory = make_session_factory()
    if args.review_queue:
        for r in review_queue(factory):
            llm = f" | LLM {r['llm_outcome']}: {r['llm_selected']} ({r['llm_confidence']}) {r['llm_reason'] or ''}" if r["llm_outcome"] else ""
            print(f"  #{r['id']:<4} {r['name']:<28} {r['chamber']:<6} {r['status']:<10}{llm}")
        return 0
    llm = None
    if args.llm or settings.politician_llm_enabled:
        from .politician_llm import build_resolver

        llm = build_resolver(settings.openai_api_key, settings.politician_llm_model)
        if llm is None:
            print("LLM resolution requested but OPENAI_API_KEY is not set; continuing without it.")
    if args.overrides:
        from .politician_overrides import OverrideError, load_overrides_file

        with factory() as session:
            try:
                rows = load_overrides_file(session, args.overrides)
                session.commit()
            except OverrideError as exc:
                session.rollback()
                print(f"Overrides rejected, nothing was recorded: {exc}")
                return 3
        print(f"Recorded {len(rows)} reviewed override(s)."
              + (f" Skipped {len(rows.skipped)} for politicians not in this database." if rows.skipped else ""))
    report = enrich_politicians(
        factory, provider, None if args.no_committees else clerk,
        stale_days=settings.politician_enrich_stale_days, retry_days=settings.politician_retry_days,
        force=args.force, only_ids=set(args.ids) if args.ids else None, limit=args.limit, dry_run=args.dry_run,
        llm=llm, llm_min_confidence=settings.politician_llm_min_confidence, llm_max_calls=settings.politician_llm_max_calls,
        llm_auto_accept=settings.politician_llm_auto_accept,
    )
    print(report.summary())
    for pid, name, bioguide in report.matched:
        print(f"  matched    #{pid:<4} {name:<28} {bioguide}")
    for u in report.unresolved:
        print(f"  {u.status:<10} #{u.politician_id:<4} {u.name:<28} {u.note}")
    for pid, name, bioguide in report.overrides_applied:
        print(f"  override   #{pid:<4} {name:<28} {bioguide} (reviewed override)")
    for pid, name, bioguide in report.llm_pending_review:
        print(f"  review     #{pid:<4} {name:<28} {bioguide} (LLM suggestion, validated; awaiting approval)")
    for pid, name, bioguide in report.llm_resolved:
        print(f"  llm        #{pid:<4} {name:<28} {bioguide} (LLM-assisted, validated)")
    if llm is not None:
        print(f"  llm calls: {report.llm_calls}, cached: {report.llm_cached}, errors: {len(report.llm_errors)}, "
              f"tokens in/out: {getattr(llm, 'tokens_in', 0)}/{getattr(llm, 'tokens_out', 0)}")
        if os.environ.get("POLTRACKER_LLM_TRACE"):
            import json as _json

            print("LLM_TRACE_JSON " + _json.dumps(report.llm_trace))
    for e in report.llm_errors:
        print(f"  llm error  {e}")
    for w in report.warnings:
        print(f"  warning    {w}")
    if report.committee_message:
        print(f"  committees: {report.committee_message}")
    return {"ok": 0, "nothing_to_do": 0, "not_configured": 2, "provider_error": 1}[report.status]


if __name__ == "__main__":
    raise SystemExit(main())
