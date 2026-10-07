"""Enrich securities with official company identifiers and industry classification.   python -m poltracker.enrich_securities

Adds CIK, SIC code, SIC description (industry), SIC division (sector), exchange and the official company name from SEC EDGAR.
Phase 1 of committee/sector context: it only stores metadata. It never changes trades, security ids, tickers, or the trade-derived
`name`, makes no committee or relevance judgement, and uses no language model. A security the source does not list is recorded as
unresolved with a reason, never guessed.

Incremental: a profile checked within PROFILE_STALE_DAYS, and an unresolved one checked within PROFILE_RETRY_DAYS, are skipped without a
request. A missing profile never affects anything else in the app.
"""

import argparse
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .db import make_session_factory
from .models import Security, Trade, _now
from .providers.base import ProviderError, ProviderRateLimited
from .providers.company_profiles import CompanyProfileProvider

log = logging.getLogger(__name__)

NOT_LISTED = "ticker is not in the SEC company ticker list (for example an ETF, fund, foreign listing or delisted name)"


@dataclass
class SecurityProfileReport:
    status: str = "ok"  # ok | provider_error | rate_limited
    message: str = ""
    considered: int = 0
    skipped_current: int = 0
    skipped_recent_attempt: int = 0
    enriched: int = 0  # ok: CIK and SIC found
    partial: int = 0  # CIK found, no SIC published
    unresolved: list[tuple[str, str]] = field(default_factory=list)  # (ticker, reason)
    errors: list[str] = field(default_factory=list)
    requests: int = 0
    dry_run: bool = False

    def summary(self) -> str:
        return (
            f"{self.status}: {self.enriched} enriched, {self.partial} partial (no SIC), {len(self.unresolved)} unresolved, "
            f"{self.skipped_current} current, {self.skipped_recent_attempt} recently tried, {len(self.errors)} errors, "
            f"{self.requests} requests{' (dry run: nothing written)' if self.dry_run else ''}" + (f" | {self.message}" if self.message else "")
        )


def enrich_securities(
    session_factory: sessionmaker[Session],
    provider: CompanyProfileProvider,
    *,
    now: datetime | None = None,
    stale_days: int = 90,
    retry_days: int = 30,
    force: bool = False,
    limit: int | None = None,
    tickers: set[str] | None = None,
    dry_run: bool = False,
) -> SecurityProfileReport:
    now = now or _now()
    report = SecurityProfileReport(dry_run=dry_run)
    with session_factory() as session:
        traded = select(Trade.security_id).where(Trade.security_id.is_not(None))
        stmt = select(Security).where(Security.id.in_(traded)).order_by(Security.id)
        if tickers:
            stmt = stmt.where(Security.ticker.in_({t.upper() for t in tickers}))
        due = []
        for sec in session.scalars(stmt):
            if not force and sec.profile_checked_at is not None:
                age = now - sec.profile_checked_at
                if sec.profile_status in ("ok", "partial") and age < timedelta(days=stale_days):
                    report.skipped_current += 1
                    continue
                if sec.profile_status == "unresolved" and age < timedelta(days=retry_days):
                    report.skipped_recent_attempt += 1
                    continue
            due.append(sec)
        due = due[:limit] if limit else due
        report.considered = len(due)
        if not due:
            return report
        try:
            provider.prepare(s.ticker for s in due)
        except ProviderRateLimited as exc:
            report.status, report.message = "rate_limited", str(exc)
            report.requests = getattr(provider, "requests_made", 0)
            return report
        except ProviderError as exc:
            report.status, report.message = "provider_error", str(exc)
            report.requests = getattr(provider, "requests_made", 0)
            return report

        done = 0
        for sec in due:
            try:
                profile = provider.get_profile(sec.ticker)
            except ProviderRateLimited as exc:
                report.status, report.message = "rate_limited", f"stopped early ({exc}); progress is saved, re-run to continue"
                break
            except ProviderError as exc:  # left unchecked, so the next run retries it
                report.errors.append(f"{sec.ticker}: {exc}")
                continue
            sec.profile_checked_at = now
            if profile is None:
                if sec.profile_status in ("ok", "partial"):  # keep what was verified earlier; just note the lookup
                    sec.profile_note = "not found in the latest SEC ticker list; earlier profile kept"[:300]
                else:
                    sec.profile_status, sec.profile_note = "unresolved", NOT_LISTED
                report.unresolved.append((sec.ticker, sec.profile_note))
            else:
                sec.company_name, sec.cik, sec.sic_code = profile.company_name, profile.cik, profile.sic_code
                sec.industry, sec.sector, sec.exchange = profile.industry, profile.sector, profile.exchange
                sec.profile_source, sec.profile_source_url = profile.source, profile.source_url
                sec.profile_updated_at = now
                if profile.sic_code:
                    sec.profile_status, sec.profile_note = "ok", None
                    report.enriched += 1
                else:
                    sec.profile_status, sec.profile_note = "partial", "the SEC publishes no SIC code for this company"
                    report.partial += 1
            done += 1
            if done % 25 == 0:  # commit in batches so an interrupted run keeps its progress (a dry run only ever rolls back)
                session.rollback() if dry_run else session.commit()
        session.rollback() if dry_run else session.commit()
    report.requests = getattr(provider, "requests_made", 0)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enrich securities with SEC EDGAR company profiles (CIK, SIC, industry, exchange)")
    parser.add_argument("--limit", type=int, help="enrich at most this many securities")
    parser.add_argument("--ticker", nargs="+", help="only these tickers")
    parser.add_argument("--force", action="store_true", help="ignore the recency rules")
    parser.add_argument("--dry-run", action="store_true", help="look up and report, write nothing")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    from .providers.company_profiles import SecEdgarProvider

    provider = SecEdgarProvider(settings.sec_user_agent, min_interval=settings.sec_request_interval)
    report = enrich_securities(
        make_session_factory(), provider, stale_days=settings.security_profile_stale_days, retry_days=settings.security_profile_retry_days,
        force=args.force, limit=args.limit, tickers=set(args.ticker) if args.ticker else None, dry_run=args.dry_run,
    )
    print(report.summary())
    for t, why in report.unresolved[:25]:
        print(f"  unresolved {t:<8} {why}")
    if len(report.unresolved) > 25:
        print(f"  ... and {len(report.unresolved) - 25} more unresolved")
    for e in report.errors[:10]:
        print(f"  error: {e}")
    return {"ok": 0, "provider_error": 1, "rate_limited": 3}[report.status]


if __name__ == "__main__":
    raise SystemExit(main())
