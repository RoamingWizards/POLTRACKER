"""Aggregate return analytics across one politician's trades in a period.

Every figure is an equal-weighted statistic over trades (each trade counts once). Disclosures give only amount ranges, so no
dollar weighting is attempted. Raw security returns are never altered; direction-adjusted figures (sells flipped) are a
separate view. Returns come from `performance.compute_performance`; nothing is recomputed here.
"""

import statistics
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from .activity import months_back, window
from .performance import TradePerformance

AnalyticsPeriod = Literal["7d", "1m", "3m", "6m", "1y", "all"]


def period_window(period: str, today: date) -> tuple[date | None, date]:
    """Inclusive window ending today; `all` has no lower bound."""
    if period == "all":
        return None, today
    if period == "1y":
        return months_back(today, 12) + timedelta(days=1), today
    return window(period, today)


@dataclass
class TradeRef:
    trade_id: int
    ticker: str | None
    transaction_type: str
    return_: float | None
    excess_return: float | None


@dataclass
class Stat:
    n: int = 0  # trades with a return
    n_benchmarked: int = 0  # of those, trades that also have a benchmark comparison
    mean_return: float | None = None
    median_return: float | None = None
    mean_benchmark_return: float | None = None
    mean_excess_return: float | None = None
    median_excess_return: float | None = None
    outperformed: int = 0  # trades whose excess return is above zero (of n_benchmarked)
    best: TradeRef | None = None  # highest excess return
    worst: TradeRef | None = None


@dataclass
class LegSummary:
    raw: Stat = field(default_factory=Stat)
    adjusted: Stat = field(default_factory=Stat)


@dataclass
class Analytics:
    start: date | None
    end: date
    trades_in_period: int = 0
    priced: int = 0
    unpriced: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=lambda: {"buys": 0, "sells": 0, "other": 0})
    transaction: LegSummary = field(default_factory=LegSummary)
    disclosure: LegSummary = field(default_factory=LegSummary)


def _mean(xs: list[float]) -> float | None:
    return statistics.fmean(xs) if xs else None


def _median(xs: list[float]) -> float | None:
    return statistics.median(xs) if xs else None


def stat(points: list[tuple[TradeRef, float | None, float | None, float | None]], with_benchmark: bool = True) -> Stat:
    """points: (trade, return, benchmark return, excess return). Trades without a return are skipped."""
    pts = [p for p in points if p[1] is not None]
    bench = [p for p in pts if p[3] is not None]
    out = Stat(n=len(pts), n_benchmarked=len(bench))
    out.mean_return = _mean([p[1] for p in pts])
    out.median_return = _median([p[1] for p in pts])
    out.mean_excess_return = _mean([p[3] for p in bench])
    out.median_excess_return = _median([p[3] for p in bench])
    out.mean_benchmark_return = _mean([p[2] for p in bench if p[2] is not None]) if with_benchmark else None
    out.outperformed = sum(1 for p in bench if p[3] > 0)
    if bench:  # ties broken by trade id so the result is deterministic
        out.best = max(bench, key=lambda p: (p[3], -p[0].trade_id))[0]
        out.worst = min(bench, key=lambda p: (p[3], p[0].trade_id))[0]
    return out


def summarize(entries: Iterable[tuple[object, TradePerformance]], start: date | None, end: date) -> Analytics:
    """entries: (trade with id/ticker/transaction_type, its performance)."""
    result = Analytics(start, end)
    legs: dict[str, tuple[list, list]] = {"transaction": ([], []), "disclosure": ([], [])}
    status = Counter()
    for trade, perf in entries:
        result.trades_in_period += 1
        kind = {"buy": "buys", "sell": "sells", "sell_partial": "sells"}.get(trade.transaction_type, "other")
        result.by_type[kind] += 1
        if perf.status == "ok":
            result.priced += 1
        else:
            status[perf.status] += 1
        for name in ("transaction", "disclosure"):
            leg = getattr(perf, name)
            if leg is None or leg.status != "ok":
                continue
            ref = lambda r, x: TradeRef(trade.id, trade.ticker, trade.transaction_type, r, x)  # noqa: E731
            legs[name][0].append((ref(leg.return_, leg.excess_return), leg.return_, leg.benchmark_return, leg.excess_return))
            adj_ret = perf.direction_adjusted.get(f"{name}_return")
            adj_ex = perf.direction_adjusted.get(f"{name}_excess_return")
            legs[name][1].append((ref(adj_ret, adj_ex), adj_ret, None, adj_ex))
    result.unpriced = dict(status)
    for name in ("transaction", "disclosure"):
        raw, adjusted = legs[name]
        setattr(result, name, LegSummary(raw=stat(raw), adjusted=stat(adjusted, with_benchmark=False)))
    return result
