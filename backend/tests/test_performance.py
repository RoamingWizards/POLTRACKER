from datetime import date, timedelta

import pytest

from poltracker.performance import (
    STATUS_INVALID_DATE,
    STATUS_NO_PRICE_AT_DATE,
    STATUS_NO_PRICES,
    STATUS_NO_TICKER,
    PriceSeries,
    compute_performance,
    transaction_date_problem,
)

HOLIDAYS = {date(2025, 11, 27), date(2025, 12, 25), date(2026, 1, 1)}  # Thanksgiving, Christmas, New Year
TODAY = date(2026, 1, 15)


def trading_days(start: date, end: date) -> list[date]:
    days, d = [], start
    while d <= end:
        if d.weekday() < 5 and d not in HOLIDAYS:
            days.append(d)
        d += timedelta(days=1)
    return days


def series(prices: dict[date, float]) -> PriceSeries:
    return PriceSeries(list(prices.items()))


# Stock: 100 on 2025-11-26 rising 1/day; benchmark: 400 flat-ish with its own moves.
DAYS = trading_days(date(2025, 11, 20), date(2026, 1, 14))
STOCK = series({d: 100 + i for i, d in enumerate(DAYS)})
BENCH = series({d: 400 + 2 * i for i, d in enumerate(DAYS)})


def perf(tx, disc=None, kind="buy", s=STOCK, b=BENCH, ticker="XYZ", today=TODAY):
    return compute_performance(
        ticker=ticker, transaction_type=kind, transaction_date=tx, disclosure_date=disc,
        series=s, benchmark=b, benchmark_ticker="SPY", today=today,
    )


def price_on(s: PriceSeries, d: date) -> float:
    return s.prices[s.dates.index(d)]


# ── trading-day anchoring ────────────────────────────────────────────────────


def test_weekend_rolls_to_next_trading_day():
    saturday = date(2025, 11, 29)
    assert saturday.weekday() == 5
    p = perf(saturday)
    assert p.transaction.anchor_date == date(2025, 12, 1)  # Monday
    assert p.transaction.price == price_on(STOCK, date(2025, 12, 1))


def test_market_holiday_rolls_to_next_trading_day():
    p = perf(date(2025, 11, 27))  # Thanksgiving (Thursday), market closed
    assert p.transaction.anchor_date == date(2025, 11, 28)


def test_holiday_that_falls_before_a_weekend_skips_both():
    p = perf(date(2025, 12, 25))  # Thursday holiday -> Friday 26th exists
    assert p.transaction.anchor_date == date(2025, 12, 26)
    q = perf(date(2026, 1, 1))  # Thursday holiday -> Friday Jan 2
    assert q.transaction.anchor_date == date(2026, 1, 2)


def test_trading_day_is_used_as_is():
    assert perf(date(2025, 12, 3)).transaction.anchor_date == date(2025, 12, 3)


def test_no_bar_within_gap_is_not_guessed():
    late_ipo = series({d: 50.0 for d in trading_days(date(2026, 1, 5), date(2026, 1, 14))})
    p = perf(date(2025, 11, 25), s=late_ipo)  # first bar is 41 days later
    assert p.status == STATUS_NO_PRICE_AT_DATE
    assert p.transaction.return_ is None


# ── invalid dates ────────────────────────────────────────────────────────────


def test_future_transaction_date_is_invalid_and_has_no_metrics():
    p = perf(date(2026, 12, 26), date(2026, 2, 9), today=date(2026, 10, 6))
    assert p.status == STATUS_INVALID_DATE
    assert "future" in p.detail
    assert p.transaction is None and p.disclosure is None
    assert p.direction_adjusted == {}


def test_transaction_after_disclosure_is_invalid():
    assert transaction_date_problem(date(2026, 1, 10), date(2026, 1, 5), TODAY)
    p = perf(date(2026, 1, 10), date(2026, 1, 5))
    assert p.status == STATUS_INVALID_DATE and "after disclosure" in p.detail


def test_valid_dates_have_no_problem():
    assert transaction_date_problem(date(2025, 12, 1), date(2025, 12, 20), TODAY) is None
    assert transaction_date_problem(date(2025, 12, 1), None, TODAY) is None


def test_future_disclosure_only_invalidates_the_disclosure_leg():
    p = perf(date(2025, 12, 1), date(2026, 3, 1))
    assert p.status == "ok" and p.transaction.status == "ok"
    assert p.disclosure.status == STATUS_INVALID_DATE and p.disclosure.return_ is None


def test_missing_ticker_and_prices():
    assert perf(date(2025, 12, 1), ticker=None).status == STATUS_NO_TICKER
    assert perf(date(2025, 12, 1), s=PriceSeries([])).status == STATUS_NO_PRICES
    assert perf(date(2025, 12, 1), s=None).status == STATUS_NO_PRICES


# ── returns ──────────────────────────────────────────────────────────────────


def test_transaction_return_uses_anchor_and_latest_adjusted_price():
    tx = date(2025, 12, 2)
    p = perf(tx)
    start, latest = price_on(STOCK, tx), STOCK.latest[1]
    assert p.latest_date == date(2026, 1, 14) and p.latest_price == latest
    assert p.transaction.return_ == pytest.approx(latest / start - 1)


def test_disclosure_return_is_measured_from_disclosure_not_transaction():
    tx, disc = date(2025, 12, 2), date(2025, 12, 18)
    p = perf(tx, disc)
    assert p.disclosure.anchor_date == disc
    assert p.disclosure.return_ == pytest.approx(STOCK.latest[1] / price_on(STOCK, disc) - 1)
    assert p.disclosure.return_ != pytest.approx(p.transaction.return_)


def test_disclosure_on_weekend_rolls_forward():
    p = perf(date(2025, 12, 2), date(2025, 12, 20))  # Saturday
    assert p.disclosure.anchor_date == date(2025, 12, 22)


def test_spy_benchmark_return_covers_same_periods():
    tx, disc = date(2025, 12, 2), date(2025, 12, 18)
    p = perf(tx, disc)
    b_latest = BENCH.latest[1]
    assert p.transaction.benchmark_return == pytest.approx(b_latest / price_on(BENCH, tx) - 1)
    assert p.disclosure.benchmark_return == pytest.approx(b_latest / price_on(BENCH, disc) - 1)
    assert p.benchmark == "SPY"


def test_benchmark_anchor_follows_the_same_rolled_date():
    p = perf(date(2025, 11, 27))  # holiday
    assert p.transaction.benchmark_return == pytest.approx(
        BENCH.latest[1] / price_on(BENCH, date(2025, 11, 28)) - 1
    )


def test_excess_return_is_security_minus_benchmark():
    tx, disc = date(2025, 12, 2), date(2025, 12, 18)
    p = perf(tx, disc)
    assert p.transaction.excess_return == pytest.approx(p.transaction.return_ - p.transaction.benchmark_return)
    assert p.disclosure.excess_return == pytest.approx(p.disclosure.return_ - p.disclosure.benchmark_return)


def test_missing_benchmark_leaves_excess_empty_but_keeps_raw_return():
    p = perf(date(2025, 12, 2), b=None)
    assert p.transaction.return_ is not None
    assert p.transaction.benchmark_return is None and p.transaction.excess_return is None


def test_no_disclosure_date_leaves_disclosure_leg_empty():
    p = perf(date(2025, 12, 2), None)
    assert p.disclosure.status == "no_date" and p.disclosure.return_ is None


# ── raw vs direction-adjusted ────────────────────────────────────────────────


def test_sell_keeps_raw_return_and_flips_only_the_adjusted_view():
    tx = date(2025, 12, 2)
    buy, sell = perf(tx, kind="buy"), perf(tx, kind="sell")
    assert sell.transaction.return_ == pytest.approx(buy.transaction.return_)  # raw unchanged
    assert sell.transaction.return_ > 0  # price rose
    assert sell.direction == -1
    assert sell.direction_adjusted["transaction_return"] == pytest.approx(-buy.transaction.return_)
    assert buy.direction_adjusted["transaction_return"] == pytest.approx(buy.transaction.return_)
    assert sell.direction_adjusted["transaction_excess_return"] == pytest.approx(-sell.transaction.excess_return)


def test_exchange_has_no_direction_adjustment():
    p = perf(date(2025, 12, 2), kind="exchange")
    assert p.direction is None
    assert p.direction_adjusted["transaction_return"] is None
    assert p.transaction.return_ is not None
