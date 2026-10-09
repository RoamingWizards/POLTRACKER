"""Trade performance from cached prices. Pure functions plus thin DB loaders.

Conventions
- Returns are fractions (0.10 == +10%) computed from adjusted close.
- An anchor price is the first bar on or after the stated date, so weekends and
  market holidays roll forward to the next trading day.
- Source dates are never altered. A trade whose dates cannot be right is reported
  as `invalid_date` and gets no price metrics; we do not guess a corrected date.
- `raw` figures describe the security. `direction_adjusted` multiplies them by +1
  for buys and -1 for sells, so a sale followed by a drop reads as positive.
"""

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import PriceBar, Security, Trade

MAX_ANCHOR_GAP_DAYS = 7  # a bar further than this after the stated date is not "the next trading day"

STATUS_OK = "ok"
STATUS_NO_TICKER = "no_ticker"
STATUS_INVALID_DATE = "invalid_date"
STATUS_NO_PRICES = "no_prices"
STATUS_NO_PRICE_AT_DATE = "no_price_at_date"
STATUS_HORIZON_NOT_ELAPSED = "horizon_not_elapsed"  # a fixed measurement window was requested and the cached prices do not reach its end


def direction(transaction_type: str) -> int | None:
    if transaction_type == "buy":
        return 1
    if transaction_type in ("sell", "sell_partial"):
        return -1
    return None  # exchange / unknown: no direction to apply


def transaction_date_problem(tx: date, disclosure: date | None, today: date) -> str | None:
    """Why a transaction date can't be trusted, or None."""
    if tx > today:
        return "transaction date is in the future"
    if disclosure is not None and tx > disclosure:
        return "transaction date is after disclosure date"
    return None


class PriceSeries:
    """Sorted daily adjusted-close series with trading-day lookups."""

    def __init__(self, points: list[tuple[date, float]]):
        pts = sorted(p for p in points if p[1] is not None)
        self.dates = [d for d, _ in pts]
        self.prices = [p for _, p in pts]

    def __bool__(self) -> bool:
        return bool(self.dates)

    @property
    def latest(self) -> tuple[date, float] | None:
        return (self.dates[-1], self.prices[-1]) if self.dates else None

    def on_or_after(self, d: date, max_gap_days: int = MAX_ANCHOR_GAP_DAYS) -> tuple[date, float] | None:
        i = bisect_left(self.dates, d)
        if i == len(self.dates) or (self.dates[i] - d).days > max_gap_days:
            return None
        return self.dates[i], self.prices[i]

    def on_or_before(self, d: date) -> tuple[date, float] | None:
        i = bisect_right(self.dates, d)
        return (self.dates[i - 1], self.prices[i - 1]) if i else None


def _ret(start: float | None, end: float | None) -> float | None:
    if start is None or end is None or start <= 0:
        return None
    return end / start - 1


def _diff(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b


def _signed(sign: int | None, value: float | None) -> float | None:
    return None if sign is None or value is None else sign * value


@dataclass
class Leg:
    """Price, return and benchmark comparison from one anchor date to the latest bar."""

    status: str
    anchor_date: date | None = None
    price: float | None = None
    return_: float | None = None
    benchmark_return: float | None = None
    excess_return: float | None = None


@dataclass
class TradePerformance:
    status: str
    detail: str | None = None
    benchmark: str | None = None
    latest_date: date | None = None
    latest_price: float | None = None
    direction: int | None = None
    transaction: Leg | None = None
    disclosure: Leg | None = None
    direction_adjusted: dict[str, float | None] = field(default_factory=dict)


def _leg(
    stated: date | None, today: date, series: PriceSeries, bench: PriceSeries, latest: tuple[date, float], horizon_days: int | None = None
) -> Leg:
    if stated is None:
        return Leg(status="no_date")
    if stated > today:
        return Leg(status=STATUS_INVALID_DATE)
    anchor = series.on_or_after(stated)
    if anchor is None or anchor[0] > latest[0]:
        return Leg(status=STATUS_NO_PRICE_AT_DATE)
    end = latest
    if horizon_days is not None:  # a fixed window from the anchor, so every trade is measured over the same length of time
        end_date = anchor[0] + timedelta(days=horizon_days)
        if latest[0] < end_date:
            return Leg(status=STATUS_HORIZON_NOT_ELAPSED, anchor_date=anchor[0], price=anchor[1])
        end = series.on_or_before(end_date)
    ret = _ret(anchor[1], end[1])
    b_anchor = bench.on_or_after(stated) if bench else None
    b_latest = bench.on_or_before(end[0]) if bench else None
    b_ret = _ret(b_anchor[1], b_latest[1]) if b_anchor and b_latest and b_anchor[0] <= b_latest[0] else None
    return Leg(
        status=STATUS_OK,
        anchor_date=anchor[0],
        price=anchor[1],
        return_=ret,
        benchmark_return=b_ret,
        excess_return=_diff(ret, b_ret),
    )


def compute_performance(
    *,
    ticker: str | None,
    transaction_type: str,
    transaction_date: date,
    disclosure_date: date | None,
    series: PriceSeries | None,
    benchmark: PriceSeries | None,
    benchmark_ticker: str,
    today: date,
    horizon_days: int | None = None,
) -> TradePerformance:
    """Without `horizon_days` every figure runs from the anchor to the latest bar. With it, from the anchor to `horizon_days` later
    (the last bar on or before that date), or `horizon_not_elapsed` when the cached prices stop sooner."""
    if not ticker:
        return TradePerformance(status=STATUS_NO_TICKER)
    problem = transaction_date_problem(transaction_date, disclosure_date, today)
    if problem:
        return TradePerformance(status=STATUS_INVALID_DATE, detail=problem)
    if not series:
        return TradePerformance(status=STATUS_NO_PRICES)

    latest = series.latest
    bench = benchmark or PriceSeries([])
    tx_leg = _leg(transaction_date, today, series, bench, latest, horizon_days)
    di_leg = _leg(disclosure_date, today, series, bench, latest, horizon_days)
    sign = direction(transaction_type)
    status = STATUS_OK if tx_leg.status == STATUS_OK else tx_leg.status
    return TradePerformance(
        status=status,
        benchmark=benchmark_ticker,
        latest_date=latest[0],
        latest_price=latest[1],
        direction=sign,
        transaction=tx_leg,
        disclosure=di_leg,
        direction_adjusted={
            "transaction_return": _signed(sign, tx_leg.return_),
            "disclosure_return": _signed(sign, di_leg.return_),
            "transaction_excess_return": _signed(sign, tx_leg.excess_return),
            "disclosure_excess_return": _signed(sign, di_leg.excess_return),
        },
    )


# ── DB loaders ────────────────────────────────────────────────────────────────


def load_series(session: Session, security_id: int) -> PriceSeries:
    rows = session.execute(
        select(PriceBar.date, PriceBar.adj_close, PriceBar.close).where(PriceBar.security_id == security_id)
    ).all()
    return PriceSeries([(d, adj if adj is not None else close) for d, adj, close in rows])


def load_benchmark(session: Session, benchmark_ticker: str) -> PriceSeries:
    sec = session.scalar(select(Security).where(Security.ticker == benchmark_ticker))
    return load_series(session, sec.id) if sec else PriceSeries([])


def trade_performance(
    trade: Trade, series: PriceSeries | None, benchmark: PriceSeries | None, benchmark_ticker: str, today: date
) -> TradePerformance:
    return compute_performance(
        ticker=trade.ticker,
        transaction_type=trade.transaction_type,
        transaction_date=trade.transaction_date,
        disclosure_date=trade.disclosure_date,
        series=series,
        benchmark=benchmark,
        benchmark_ticker=benchmark_ticker,
        today=today,
    )
