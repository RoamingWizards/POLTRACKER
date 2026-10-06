"""Incremental ingestion: newest-first pages until a page contains nothing new.

State lives in the database (fingerprints), not in memory, so a restart or a
second run never re-inserts anything. An empty database backfills up to
`max_pages`; a caught-up database costs a single request.
"""

import argparse
import logging
import time
from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .db import make_session_factory
from .domain import TradeIn
from .models import IngestState, Politician, Security, Trade
from .normalize import fingerprint, politician_key
from .providers import CongressInvestsProvider, CongressProvider, ProviderError

log = logging.getLogger(__name__)


@dataclass
class IngestResult:
    pages: int = 0
    fetched: int = 0
    inserted: int = 0
    skipped: int = 0
    stopped: str = ""


def _get_politician(session: Session, trade: TradeIn, cache: dict[str, Politician]) -> Politician:
    key = politician_key(trade.politician_name, trade.chamber)
    pol = cache.get(key) or session.scalar(select(Politician).where(Politician.canonical_key == key))
    if pol is None:
        pol = Politician(canonical_key=key, name=trade.politician_name, chamber=trade.chamber)
        session.add(pol)
    pol.party = pol.party or trade.party
    pol.state = pol.state or trade.state
    cache[key] = pol
    return pol


def _get_security(session: Session, trade: TradeIn, cache: dict[str, Security]) -> Security | None:
    if not trade.ticker:
        return None
    sec = cache.get(trade.ticker) or session.scalar(select(Security).where(Security.ticker == trade.ticker))
    if sec is None:
        sec = Security(ticker=trade.ticker, name=trade.asset_name)
        session.add(sec)
    sec.name = sec.name or trade.asset_name
    cache[trade.ticker] = sec
    return sec


def store_trades(session: Session, trades: list[TradeIn], seen: Counter) -> int:
    """Insert trades whose fingerprint is not already stored. Returns the number inserted.

    `seen` counts base occurrences across the whole run so identical lines in one
    filing get distinct, deterministic fingerprints.
    """
    keyed: list[tuple[str, TradeIn]] = []
    for trade in trades:
        base = fingerprint(trade, 0)
        keyed.append((fingerprint(trade, seen[base]), trade))
        seen[base] += 1

    fps = [fp for fp, _ in keyed]
    existing = set(session.scalars(select(Trade.fingerprint).where(Trade.fingerprint.in_(fps)))) if fps else set()

    pol_cache: dict[str, Politician] = {}
    sec_cache: dict[str, Security] = {}
    inserted = 0
    for fp, trade in keyed:
        if fp in existing:
            continue
        existing.add(fp)
        pol = _get_politician(session, trade, pol_cache)
        sec = _get_security(session, trade, sec_cache)
        session.add(
            Trade(
                source=trade.source,
                source_trade_id=trade.source_trade_id,
                fingerprint=fp,
                politician=pol,
                security=sec,
                politician_name=trade.politician_name,
                chamber=trade.chamber,
                party=trade.party,
                state=trade.state,
                ticker=trade.ticker,
                asset_name=trade.asset_name,
                transaction_type=trade.transaction_type,
                transaction_date=trade.transaction_date,
                disclosure_date=trade.disclosure_date,
                amount_min=trade.amount_min,
                amount_max=trade.amount_max,
                source_url=trade.source_url,
            )
        )
        inserted += 1
    session.flush()
    return inserted


def _backfill_state(session: Session, source: str, page_size: int) -> tuple[bool, int]:
    """(backfill_complete, page to start from).

    Once complete, runs start at the newest page. Before that, a run resumes near where the
    stored data ends, one page back for overlap because upstream order within tied filing
    dates is not guaranteed to be stable between requests.
    """
    state = session.get(IngestState, source)
    if state and state.backfill_complete:
        return True, 0
    stored = session.scalar(select(func.count(Trade.id)).where(Trade.source == source)) or 0
    return False, max(0, stored // page_size - 1)


def _mark_complete(session: Session, source: str) -> None:
    state = session.get(IngestState, source)
    if state is None:
        session.add(IngestState(source=source, backfill_complete=True))
    else:
        state.backfill_complete = True


def ingest_recent(
    provider: CongressProvider,
    session_factory: sessionmaker[Session],
    *,
    page_size: int,
    max_pages: int,
) -> IngestResult:
    result = IngestResult()
    seen: Counter = Counter()
    with session_factory() as session:
        complete, start_page = _backfill_state(session, provider.name, page_size)
    try:
        for page in provider.iter_recent_pages(page_size=page_size, max_pages=max_pages, start_page=start_page):
            with session_factory() as session:
                inserted = store_trades(session, page.trades, seen)
                if not page.has_more:
                    _mark_complete(session, provider.name)  # reached the end of the provider's data
                session.commit()  # commit per page so partial progress survives a failure
            result.pages += 1
            result.fetched += len(page.trades)
            result.skipped += page.skipped
            result.inserted += inserted
            if not page.has_more:
                result.stopped = "reached the end of the provider's data"
                break
            if inserted == 0 and complete:
                result.stopped = "caught up (page had nothing new)"
                break
        else:
            result.stopped = "reached max_pages; backfill will resume next run" if not complete else "reached max_pages"
    except ProviderError as exc:
        result.stopped = f"provider error: {exc}"
        log.error("Ingestion stopped early: %s", exc)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest recent congressional trades")
    parser.add_argument("--loop", action="store_true", help="repeat every INGEST_INTERVAL_HOURS")
    parser.add_argument("--enrich", action="store_true", help="fetch missing prices after each ingest")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    session_factory = make_session_factory()
    provider = CongressInvestsProvider(settings.congressinvests_base_url, settings.congressinvests_api_key)

    while True:
        before = provider.requests_made
        result = ingest_recent(
            provider, session_factory, page_size=settings.ingest_page_size, max_pages=settings.ingest_max_pages
        )
        log.info("%s | requests used this run: %d", result, provider.requests_made - before)
        if args.enrich:
            from .enrich import enrich
            from .providers.prices import YFinanceProvider

            refresh, _ = enrich(YFinanceProvider(), session_factory)
            log.info("prices: enriched=%d cached=%d unavailable=%d failed=%d",
                     refresh.enriched, refresh.cached, len(refresh.unavailable), len(refresh.failed))
        if not args.loop:
            return
        time.sleep(settings.ingest_interval_hours * 3600)


if __name__ == "__main__":
    main()
