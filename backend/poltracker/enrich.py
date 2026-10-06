"""Fetch missing prices, then report performance coverage.  python -m poltracker.enrich"""

import argparse
import logging
from collections import Counter
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .db import make_session_factory
from .models import Trade
from .performance import PriceSeries, load_benchmark, load_series, trade_performance
from .prices import RefreshResult, refresh_prices
from .providers.prices import PriceProvider, YFinanceProvider

log = logging.getLogger(__name__)


def enrich(
    provider: PriceProvider, session_factory: sessionmaker[Session], today: date | None = None
) -> tuple[RefreshResult, Counter]:
    s = get_settings()
    result = refresh_prices(
        provider,
        session_factory,
        benchmark_ticker=s.benchmark_ticker,
        batch_size=s.price_batch_size,
        retry_days=s.price_retry_days,
        overlap_days=s.price_tail_overlap_days,
        today=today,
    )
    return result, performance_coverage(session_factory, s.benchmark_ticker, today or date.today())


def performance_coverage(session_factory: sessionmaker[Session], benchmark_ticker: str, today: date) -> Counter:
    """Count trades by performance status (overall and for the disclosure leg)."""
    counts: Counter = Counter()
    with session_factory() as session:
        bench = load_benchmark(session, benchmark_ticker)
        cache: dict[int, PriceSeries] = {}
        for trade in session.scalars(select(Trade)):
            series = None
            if trade.security_id:
                series = cache.get(trade.security_id) or cache.setdefault(
                    trade.security_id, load_series(session, trade.security_id)
                )
            perf = trade_performance(trade, series, bench, benchmark_ticker, today)
            counts[f"transaction:{perf.status}"] += 1
            if perf.disclosure:
                counts[f"disclosure:{perf.disclosure.status}"] += 1
    return counts


def main() -> None:
    argparse.ArgumentParser(description="Fetch missing prices and report coverage").parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result, coverage = enrich(YFinanceProvider(), make_session_factory())
    print(f"securities considered (incl. benchmark): {result.considered}")
    print(f"  enriched this run:   {result.enriched}  ({result.bars_written} bars written)")
    print(f"  already cached:      {result.cached}")
    print(f"  unavailable:         {len(result.unavailable)}  {result.unavailable[:15]}")
    print(f"  deferred (retry):    {len(result.deferred)}")
    print(f"  failed (will retry): {len(result.failed)}  {result.failed[:15]}")
    print(f"  no valid dates:      {len(result.no_valid_dates)}  {result.no_valid_dates[:15]}")
    print(f"  adj-close restated:  {len(result.refetched_for_adjustment)}")
    print(f"invalid-date trades: {result.invalid_date_trades}")
    print("performance coverage:", dict(sorted(coverage.items())))


if __name__ == "__main__":
    main()
