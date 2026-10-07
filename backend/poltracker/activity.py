"""Buy/sell activity for one security over a recent period, bucketed for a chart.

Counts trades (exact), not dollars: disclosures only give amount ranges, so the ranges are summed separately as
reported lower/upper bounds and never turned into a single value.
"""

import calendar
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

Period = Literal["7d", "1m", "3m", "6m"]
Basis = Literal["disclosure", "transaction"]
Bucket = Literal["day", "week", "month"]

PERIODS: dict[str, tuple[int, str]] = {"7d": (0, "day"), "1m": (1, "week"), "3m": (3, "week"), "6m": (6, "month")}
BUY_TYPES = {"buy"}
SELL_TYPES = {"sell", "sell_partial"}


def months_back(d: date, n: int) -> date:
    year, month = d.year, d.month - n
    while month <= 0:
        month += 12
        year -= 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def window(period: str, end: date) -> tuple[date, date]:
    """The inclusive window ending today. 7d is exactly seven days; Nm starts the day after N calendar months back."""
    if period == "7d":
        return end - timedelta(days=6), end
    return months_back(end, PERIODS[period][0]) + timedelta(days=1), end


def buckets(start: date, end: date, kind: str) -> list[tuple[date, date]]:
    """Contiguous (first day, last day) ranges that exactly cover the window, so nothing is double counted or dropped."""
    out: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        if kind == "day":
            last = cursor
        elif kind == "week":
            last = min(cursor + timedelta(days=6), end)
        else:  # calendar months, clipped to the window
            last = min(date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1]), end)
        out.append((cursor, last))
        cursor = last + timedelta(days=1)
    return out


@dataclass
class BucketCount:
    start: date
    end: date
    buys: int = 0
    sells: int = 0
    other: int = 0


@dataclass
class Totals:
    buys: int = 0
    sells: int = 0
    other: int = 0
    buy_amount_min: int = 0
    buy_amount_max: int = 0
    sell_amount_min: int = 0
    sell_amount_max: int = 0
    trades_without_amount: int = 0

    @property
    def net(self) -> int:
        return self.buys - self.sells


@dataclass
class Activity:
    start: date
    end: date
    bucket: str
    buckets: list[BucketCount] = field(default_factory=list)
    totals: Totals = field(default_factory=Totals)

    @property
    def lean(self) -> str:
        t = self.totals
        if t.buys == 0 and t.sells == 0:
            return "no_activity"
        return "more_bought" if t.buys > t.sells else "more_sold" if t.sells > t.buys else "balanced"


def compute_activity(
    rows: Iterable[tuple[str, date, int | None, int | None]], period: str, end: date
) -> Activity:
    """rows: (transaction_type, the date being bucketed, amount_min, amount_max). Rows outside the window are ignored."""
    start, end = window(period, end)
    kind = PERIODS[period][1]
    result = Activity(start, end, kind, [BucketCount(a, b) for a, b in buckets(start, end, kind)])
    for ttype, when, lo, hi in rows:
        if not start <= when <= end:
            continue
        bucket = next(b for b in result.buckets if b.start <= when <= b.end)
        t = result.totals
        if ttype in BUY_TYPES:
            bucket.buys += 1
            t.buys += 1
            t.buy_amount_min += lo or 0
            t.buy_amount_max += hi or 0
        elif ttype in SELL_TYPES:
            bucket.sells += 1
            t.sells += 1
            t.sell_amount_min += lo or 0
            t.sell_amount_max += hi or 0
        else:  # exchanges and unrecognised types are counted but are neither a buy nor a sell
            bucket.other += 1
            t.other += 1
            continue
        if lo is None and hi is None:
            t.trades_without_amount += 1
    return result
