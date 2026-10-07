"""Buy/sell activity per ticker: windows, buckets, counting rules and the endpoint."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from poltracker.activity import buckets, compute_activity, months_back, window
from poltracker.api.main import create_app, get_session
from poltracker.config import Settings
from poltracker.models import Politician, Security, Trade

END = date(2026, 10, 7)


# --- windows --------------------------------------------------------------------------------------------------

def test_seven_days_is_exactly_seven_days_including_today():
    start, end = window("7d", END)
    assert (start, end) == (date(2026, 10, 1), END) and (end - start).days + 1 == 7


@pytest.mark.parametrize("period,start", [("1m", date(2026, 9, 8)), ("3m", date(2026, 7, 8)), ("6m", date(2026, 4, 8))])
def test_month_windows_start_the_day_after_n_calendar_months_back(period, start):
    assert window(period, END) == (start, END)


def test_month_arithmetic_clamps_to_the_end_of_shorter_months():
    assert months_back(date(2026, 3, 31), 1) == date(2026, 2, 28)
    assert months_back(date(2024, 3, 31), 1) == date(2024, 2, 29)  # leap year
    assert months_back(date(2026, 1, 15), 3) == date(2025, 10, 15)  # across the year boundary
    assert window("1m", date(2026, 3, 31))[0] == date(2026, 3, 1)


# --- buckets --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("period", ["7d", "1m", "3m", "6m"])
@pytest.mark.parametrize("end", [date(2026, 10, 7), date(2026, 3, 31), date(2024, 2, 29), date(2026, 1, 1), date(2026, 12, 31)])
def test_buckets_exactly_cover_the_window_without_gaps_or_overlap(period, end):
    start, last = window(period, end)
    from poltracker.activity import PERIODS

    parts = buckets(start, last, PERIODS[period][1])
    assert parts[0][0] == start and parts[-1][1] == last
    for (a, b), (c, _d) in zip(parts, parts[1:]):
        assert b + timedelta(days=1) == c and a <= b
    assert sum((b - a).days + 1 for a, b in parts) == (last - start).days + 1


def test_bucket_sizes_per_period():
    assert len(compute_activity([], "7d", END).buckets) == 7  # daily
    assert {(b.end - b.start).days for b in compute_activity([], "3m", END).buckets[:-1]} == {6}  # weekly
    months = compute_activity([], "6m", END).buckets  # calendar months, first one clipped to the window
    assert [b.start.month for b in months] == [4, 5, 6, 7, 8, 9, 10] and months[0].start == date(2026, 4, 8)


# --- counting -------------------------------------------------------------------------------------------------

def row(kind, when, lo=None, hi=None):
    return (kind, when, lo, hi)


def test_buys_and_sells_are_counted_in_the_right_buckets_and_totals():
    act = compute_activity(
        [row("buy", date(2026, 10, 7), 1001, 15000), row("buy", date(2026, 10, 7), 15001, 50000), row("sell", date(2026, 10, 3), 1001, 15000),
         row("sell_partial", date(2026, 10, 1), 15001, 50000)],
        "7d", END,
    )
    by_day = {b.start: (b.buys, b.sells) for b in act.buckets}
    assert by_day[date(2026, 10, 7)] == (2, 0) and by_day[date(2026, 10, 3)] == (0, 1) and by_day[date(2026, 10, 1)] == (0, 1)
    t = act.totals
    assert (t.buys, t.sells, t.other, t.net) == (2, 2, 0, 0)  # a partial sale is a sell
    assert (t.buy_amount_min, t.buy_amount_max, t.sell_amount_min, t.sell_amount_max) == (16002, 65000, 16002, 65000)
    assert act.lean == "balanced"


def test_lean_follows_the_trade_counts():
    more_buys = compute_activity([row("buy", END), row("buy", END), row("sell", END)], "7d", END)
    more_sells = compute_activity([row("sell", END), row("sell", END), row("buy", END)], "7d", END)
    assert (more_buys.lean, more_sells.lean) == ("more_bought", "more_sold")
    assert compute_activity([], "7d", END).lean == "no_activity"
    assert compute_activity([row("exchange", END)], "7d", END).lean == "no_activity"  # an exchange is neither


def test_exchanges_and_unknown_types_are_counted_separately_and_not_as_buys_or_sells():
    act = compute_activity([row("exchange", END, 1, 2), row("unknown", END), row("buy", END)], "7d", END)
    t = act.totals
    assert (t.buys, t.sells, t.other) == (1, 0, 2) and t.buy_amount_max == 0 and act.buckets[-1].other == 2


def test_window_edges_are_inclusive_and_everything_outside_is_ignored():
    start = date(2026, 10, 1)
    rows = [row("buy", start), row("buy", END), row("buy", start - timedelta(days=1)), row("buy", END + timedelta(days=1))]
    t = compute_activity(rows, "7d", END).totals
    assert t.buys == 2  # first and last day count; the day before and the future do not


def test_trades_without_any_amount_are_noted_and_do_not_distort_the_sums():
    t = compute_activity([row("buy", END, None, None), row("sell", END, 1001, 15000), row("buy", END, 1001, None)], "7d", END).totals
    assert t.trades_without_amount == 1 and (t.buys, t.sells) == (2, 1) and (t.buy_amount_min, t.buy_amount_max) == (1001, 0)


# --- endpoint -------------------------------------------------------------------------------------------------

@pytest.fixture
def client(session_factory, monkeypatch):
    monkeypatch.setattr("poltracker.api.main._today", lambda: END)
    app = create_app(Settings(_env_file=None))

    def override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    with session_factory() as s:
        pol = Politician(canonical_key="house:a", name="A", chamber="house")
        sec, other = Security(ticker="NVDA", name="Nvidia"), Security(ticker="AAPL", name="Apple")
        s.add_all([pol, sec, other, Security(ticker="MSFT", name="Microsoft")])
        s.flush()

        def trade(security, kind, tx, disc, n, lo=1001, hi=15000):
            s.add(Trade(source="t", fingerprint=f"f{n}", politician_id=pol.id, security_id=security.id, politician_name="A", chamber="house",
                        ticker=security.ticker, transaction_type=kind, transaction_date=tx, disclosure_date=disc, amount_min=lo, amount_max=hi))

        d = timedelta
        trade(sec, "buy", END - d(days=40), END - d(days=2), 1)       # old trade, disclosed this week
        trade(sec, "buy", END - d(days=40), END - d(days=3), 2)
        trade(sec, "sell", END - d(days=5), END - d(days=1), 3)       # recent trade, recent disclosure
        trade(sec, "sell", END - d(days=230), END - d(days=200), 4)   # outside even six months
        trade(sec, "buy", END - d(days=4), None, 5)                   # no disclosure date
        trade(other, "sell", END - d(days=2), END - d(days=1), 6)     # a different ticker never leaks in
        s.commit()
    return TestClient(app)


def test_the_default_is_three_months_by_disclosure_date(client):
    body = client.get("/securities/NVDA/activity").json()
    assert (body["period"], body["basis"], body["bucket"], body["end"]) == ("3m", "disclosure", "week", "2026-10-07")
    t = body["totals"]
    assert (t["buys"], t["sells"], t["net"], body["lean"]) == (2, 1, 1, "more_bought")
    assert body["undated"] == 1  # the trade with no disclosure date is reported, not silently dropped
    assert sum(b["buys"] + b["sells"] for b in body["buckets"]) == 3


def test_the_basis_changes_which_date_is_used(client):
    body = client.get("/securities/NVDA/activity?period=7d&basis=transaction").json()
    assert body["totals"]["buys"] == 1 and body["totals"]["sells"] == 1  # only the trades made in the last 7 days
    assert body["undated"] == 0 and len(body["buckets"]) == 7 and body["bucket"] == "day"
    by_disclosure = client.get("/securities/NVDA/activity?period=7d&basis=disclosure").json()["totals"]
    assert (by_disclosure["buys"], by_disclosure["sells"]) == (2, 1)  # two older trades were disclosed this week


@pytest.mark.parametrize("period,bucket", [("7d", "day"), ("1m", "week"), ("3m", "week"), ("6m", "month")])
def test_every_period_is_available(client, period, bucket):
    body = client.get(f"/securities/NVDA/activity?period={period}").json()
    assert body["period"] == period and body["bucket"] == bucket and body["buckets"][-1]["end"] == "2026-10-07"


def test_amounts_are_reported_as_range_bounds_not_a_value(client):
    t = client.get("/securities/NVDA/activity?period=7d").json()["totals"]
    assert (t["buy_amount_min"], t["buy_amount_max"]) == (2002, 30000) and (t["sell_amount_min"], t["sell_amount_max"]) == (1001, 15000)


def test_another_tickers_trades_are_isolated(client):
    t = client.get("/securities/AAPL/activity?period=7d").json()
    assert (t["totals"]["buys"], t["totals"]["sells"], t["lean"]) == (0, 1, "more_sold")


def test_a_ticker_with_no_trades_in_the_window_is_an_empty_state_not_an_error(client):
    body = client.get("/securities/MSFT/activity?period=1m").json()
    assert body["lean"] == "no_activity" and body["totals"]["buys"] == body["totals"]["sells"] == body["totals"]["net"] == 0
    assert body["buckets"] and all(b["buys"] == b["sells"] == b["other"] == 0 for b in body["buckets"])  # zero-filled, chartable
    quiet = client.get("/securities/AAPL/activity?period=1m&basis=transaction").json()
    assert quiet["totals"]["sells"] == 1 and quiet["lean"] == "more_sold"


def test_unknown_ticker_and_invalid_parameters_are_rejected(client):
    assert client.get("/securities/NOPE/activity").status_code == 404
    assert client.get("/securities/NVDA/activity?period=2w").status_code == 422
    assert client.get("/securities/NVDA/activity?basis=nonsense").status_code == 422
    assert client.get("/securities/nvda/activity").status_code == 200  # tickers are case-insensitive like the other routes
