"""Price cache: fetch only what is missing, store it in price_bars, remember coverage.

Coverage lives on the securities row (price_from..price_to = the range already
requested from the provider). That is what stops weekends, holidays, late IPOs and
dead tickers from being requested again. Bars are replaced per range with
delete + insert, which keeps this portable beyond SQLite.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session, sessionmaker

from .models import PriceBar, Security, Trade
from .performance import transaction_date_problem
from .providers.prices import PriceBarIn, PriceProvider, PriceProviderError

log = logging.getLogger(__name__)

BENCHMARK_NAMES = {"SPY": "SPDR S&P 500 ETF Trust"}
ADJ_DRIFT_TOLERANCE = 1e-4  # a changed adj_close on an old bar means a dividend/split restated history
MIN_SPAN_TO_CALL_UNAVAILABLE = 7  # don't brand a ticker dead from a request covering only a few days
MIN_BATCH_FOR_TOTAL_FAILURE = 3  # an all-empty batch this big is a provider failure, not 'no data'


@dataclass
class RefreshResult:
    considered: int = 0
    enriched: int = 0  # fetched and stored bars this run
    cached: int = 0  # already covered, no network call
    unavailable: list[str] = field(default_factory=list)  # provider returned nothing
    deferred: list[str] = field(default_factory=list)  # unavailable recently; retry window not elapsed
    no_valid_dates: list[str] = field(default_factory=list)  # every trade for it has an invalid date
    failed: list[str] = field(default_factory=list)  # batch errored; will be retried next run
    too_recent: list[str] = field(default_factory=list)
    refetched_for_adjustment: list[str] = field(default_factory=list)
    bars_written: int = 0
    invalid_date_trades: list[tuple[int, str, str]] = field(default_factory=list)  # (id, ticker, problem)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_or_create_benchmark(session: Session, ticker: str) -> Security:
    sec = session.scalar(select(Security).where(Security.ticker == ticker))
    if sec is None:
        sec = Security(ticker=ticker, name=BENCHMARK_NAMES.get(ticker))
        session.add(sec)
        session.flush()
    return sec


def needed_starts(session: Session, today: date, result: RefreshResult) -> dict[int, date]:
    """Earliest valid stated date (transaction or disclosure) per security."""
    starts: dict[int, date] = {}
    rows = session.execute(
        select(Trade.id, Trade.security_id, Trade.ticker, Trade.transaction_date, Trade.disclosure_date).where(
            Trade.security_id.is_not(None)
        )
    ).all()
    for trade_id, sec_id, ticker, tx, disc in rows:
        problem = transaction_date_problem(tx, disc, today)
        if problem:
            result.invalid_date_trades.append((trade_id, ticker, problem))
            log.warning("Trade %s (%s): %s (%s); skipping price enrichment", trade_id, ticker, problem, tx)
            continue
        candidates = [tx] + ([disc] if disc and disc <= today else [])
        starts[sec_id] = min(starts.get(sec_id, today), *candidates)
    return starts


def _plan(sec: Security, start: date, today: date, retry_days: int, overlap: int) -> tuple[date, date] | None | str:
    """The (start, end) still missing for one security, None if cached, or 'deferred'."""
    if sec.price_status == "unavailable" and sec.price_checked_at:
        if _now() - sec.price_checked_at < timedelta(days=retry_days):
            return "deferred"
    if sec.price_from is None or sec.price_to is None:
        return start, today
    head = start < sec.price_from
    tail = sec.price_to < today
    if head and tail:
        return start, today
    if head:
        return start, sec.price_from
    if tail:
        return sec.price_to - timedelta(days=overlap), today
    return None


def _replace_bars(
    session: Session, sec: Security, bars: list[PriceBarIn], lo: date, hi: date, provider: str, whole: bool = False
) -> None:
    clause = [PriceBar.security_id == sec.id]
    if not whole:
        clause += [PriceBar.date >= lo, PriceBar.date <= hi]
    session.execute(delete(PriceBar).where(*clause))
    if bars:
        session.execute(
            insert(PriceBar),
            [
                dict(security_id=sec.id, date=b.date, open=b.open, high=b.high, low=b.low, close=b.close,
                     adj_close=b.adj_close, volume=b.volume, provider=provider)
                for b in bars
            ],
        )


def _drifted(session: Session, sec: Security, bars: list[PriceBarIn]) -> bool:
    """True if stored adj_close for a date we just re-fetched has since been restated."""
    if not bars:
        return False
    stored = dict(
        session.execute(
            select(PriceBar.date, PriceBar.adj_close).where(
                PriceBar.security_id == sec.id, PriceBar.date >= bars[0].date, PriceBar.date <= bars[-1].date
            )
        ).all()
    )
    for b in bars:
        old = stored.get(b.date)
        if old and b.adj_close and abs(b.adj_close / old - 1) > ADJ_DRIFT_TOLERANCE:
            return True
    return False


def refresh_prices(
    provider: PriceProvider,
    session_factory: sessionmaker[Session],
    *,
    benchmark_ticker: str = "SPY",
    batch_size: int = 40,
    retry_days: int = 7,
    overlap_days: int = 7,
    today: date | None = None,
) -> RefreshResult:
    today = today or date.today()
    result = RefreshResult()

    with session_factory() as session:
        starts = needed_starts(session, today, result)
        bench = get_or_create_benchmark(session, benchmark_ticker)
        if starts:
            starts[bench.id] = min(starts.values())  # benchmark must reach back as far as any trade
        session.commit()

        securities = {s.id: s for s in session.scalars(select(Security).where(Security.id.in_(list(starts))))}
        all_trade_secs = set(
            session.scalars(select(Trade.security_id).where(Trade.security_id.is_not(None)).distinct())
        )
        for sec_id in all_trade_secs - set(starts):
            result.no_valid_dates.append(session.get(Security, sec_id).ticker)

    plans: list[tuple[date, date, int]] = []
    result.considered = len(securities)
    with session_factory() as session:
        for sec_id, start in starts.items():
            sec = session.get(Security, sec_id)
            plan = _plan(sec, start, today, retry_days, overlap_days)
            if plan == "deferred":
                result.deferred.append(sec.ticker)
            elif plan is None:
                result.cached += 1
            else:
                plans.append((plan[0], plan[1], sec_id))

    plans.sort()  # similar start dates batch together, so a chunk wastes little overlap
    full_refetch: list[tuple[date, int]] = []

    for i in range(0, len(plans), batch_size):
        chunk = plans[i : i + batch_size]
        _fetch_chunk(provider, session_factory, chunk, starts, today, result, full_refetch)

    # Adjusted closes were restated for these (dividend/split): rebuild their whole history.
    for i in range(0, len(full_refetch), batch_size):
        chunk = [(start, today, sec_id) for start, sec_id in full_refetch[i : i + batch_size]]
        _fetch_chunk(provider, session_factory, chunk, starts, today, result, [], whole=True)

    return result


def _fetch_chunk(provider, session_factory, chunk, starts, today, result, full_refetch, whole=False) -> None:
    with session_factory() as session:
        secs = {sec_id: session.get(Security, sec_id) for _, _, sec_id in chunk}
        tickers = [secs[sec_id].ticker for _, _, sec_id in chunk]
        lo, hi = min(c[0] for c in chunk), max(c[1] for c in chunk)
        try:
            data = provider.fetch_daily(tickers, lo, hi)
        except PriceProviderError as exc:
            log.error("Price batch failed (%d tickers): %s", len(tickers), exc)
            result.failed.extend(tickers)
            return
        if not data and len(tickers) >= MIN_BATCH_FOR_TOTAL_FAILURE:
            log.error("Price batch returned nothing for %d tickers; treating as a provider failure", len(tickers))
            result.failed.extend(tickers)
            return

        for start, end, sec_id in chunk:
            sec = secs[sec_id]
            bars = [b for b in data.get(sec.ticker, []) if start <= b.date <= end]
            had_coverage = sec.price_from is not None
            if not bars and not had_coverage:
                if (end - start).days >= MIN_SPAN_TO_CALL_UNAVAILABLE:
                    sec.price_status, sec.price_checked_at = "unavailable", _now()
                    result.unavailable.append(sec.ticker)
                else:
                    result.too_recent.append(sec.ticker)
                continue
            if whole and not bars:
                result.failed.append(sec.ticker)  # never wipe stored history on an empty rebuild
                continue
            if not whole and had_coverage and _drifted(session, sec, bars):
                full_refetch.append((starts[sec_id], sec_id))
                result.refetched_for_adjustment.append(sec.ticker)
                continue
            _replace_bars(session, sec, bars, start, end, provider.name, whole=whole)
            sec.price_from = start if whole or not had_coverage else min(sec.price_from, start)
            sec.price_to = end if whole or not had_coverage else max(sec.price_to, end)
            sec.price_status, sec.price_checked_at = "ok", _now()
            result.bars_written += len(bars)
            result.enriched += 1
        session.commit()
