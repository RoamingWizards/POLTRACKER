"""Aggregate return analytics per politician: hand-computed expectations over a small known price history."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from poltracker.api.main import create_app, get_session
from poltracker.config import Settings
from poltracker.models import PriceBar, Politician, Security, Trade
from poltracker.performance import Leg, TradePerformance
from poltracker.politician_analytics import period_window, stat, summarize, TradeRef

END = date(2026, 10, 7)
approx = pytest.approx


# --- pure aggregation -----------------------------------------------------------------------------------------

def ref(i):
    return TradeRef(i, f"T{i}", "buy", None, None)


def test_stat_computes_equal_weighted_means_medians_and_the_win_count():
    pts = [(ref(1), 0.10, 0.04, 0.06), (ref(2), -0.20, 0.04, -0.24), (ref(3), 0.50, 0.04, 0.46)]
    s = stat(pts)
    assert (s.n, s.n_benchmarked, s.outperformed) == (3, 3, 2)
    assert s.mean_return == approx(0.4 / 3) and s.median_return == approx(0.10)
    assert s.mean_excess_return == approx(0.28 / 3) and s.median_excess_return == approx(0.06) and s.mean_benchmark_return == approx(0.04)
    assert (s.best.trade_id, s.worst.trade_id) == (3, 2)  # by excess return


def test_stat_handles_missing_benchmarks_and_empty_input():
    s = stat([(ref(1), 0.10, None, None), (ref(2), 0.30, 0.1, 0.2)])
    assert (s.n, s.n_benchmarked) == (2, 1) and s.mean_return == approx(0.2) and s.mean_excess_return == approx(0.2)
    assert s.outperformed == 1 and s.best.trade_id == 2
    empty = stat([])
    assert (empty.n, empty.mean_return, empty.median_excess_return, empty.best) == (0, None, None, None)
    assert stat([(ref(1), None, None, None)]).n == 0  # a trade without a return is not counted


def test_matching_the_benchmark_exactly_is_not_outperforming():
    s = stat([(ref(1), 0.10, 0.10, 0.0), (ref(2), 0.11, 0.10, 0.01)])
    assert s.n_benchmarked == 2 and s.outperformed == 1  # only a strictly positive excess return counts


def test_ties_are_broken_deterministically_by_trade_id():
    s = stat([(ref(2), 0.1, 0.0, 0.1), (ref(1), 0.1, 0.0, 0.1)])
    assert (s.best.trade_id, s.worst.trade_id) == (1, 1)


def perf(status="ok", tx=(0.2, 0.1, 0.1), di=(0.1, 0.05, 0.05), sign=1):
    leg = lambda v: None if v is None else Leg("ok", date(2026, 1, 1), 1.0, v[0], v[1], v[2])  # noqa: E731
    adj = {}
    if tx and di:
        adj = {"transaction_return": None if sign is None else sign * tx[0], "transaction_excess_return": None if sign is None else sign * tx[2],
               "disclosure_return": None if sign is None else sign * di[0], "disclosure_excess_return": None if sign is None else sign * di[2]}
    return TradePerformance(status=status, direction=sign, transaction=leg(tx), disclosure=leg(di), direction_adjusted=adj)


class T:
    def __init__(self, i, kind="buy", ticker="X"):
        self.id, self.transaction_type, self.ticker = i, kind, ticker


def test_summarize_counts_types_and_unpriced_reasons_and_keeps_raw_and_adjusted_separate():
    a = summarize(
        [(T(1), perf()), (T(2, "sell"), perf(tx=(0.5, 0.1, 0.4), di=(0.3, 0.1, 0.2), sign=-1)),
         (T(3), TradePerformance(status="no_prices")), (T(4, "exchange"), perf(sign=None))],
        None, END,
    )
    assert (a.trades_in_period, a.priced) == (4, 3)
    assert a.by_type == {"buys": 2, "sells": 1, "other": 1} and a.unpriced == {"no_prices": 1}
    raw, adj = a.transaction.raw, a.transaction.adjusted
    assert raw.n == 3 and raw.mean_return == approx((0.2 + 0.5 + 0.2) / 3)  # raw returns are never flipped
    assert adj.n == 2 and adj.mean_return == approx((0.2 - 0.5) / 2)  # the exchange has no direction, so it is left out
    assert a.transaction.adjusted.mean_benchmark_return is None  # a benchmark has no direction to adjust


def test_an_exchange_has_a_raw_return_but_no_direction_adjusted_return():
    a = summarize([(T(1, "exchange"), perf(sign=None))], None, END)
    assert a.transaction.raw.n == 1 and a.transaction.adjusted.n == 0


@pytest.mark.parametrize("period,start", [("7d", date(2026, 10, 1)), ("1m", date(2026, 9, 8)), ("3m", date(2026, 7, 8)),
                                          ("6m", date(2026, 4, 8)), ("1y", date(2025, 10, 8)), ("all", None)])
def test_period_windows_including_one_year_and_all(period, start):
    assert period_window(period, END) == (start, END)


# --- endpoint with a real price history -----------------------------------------------------------------------

@pytest.fixture
def client(session_factory, monkeypatch):
    monkeypatch.setattr("poltracker.api.main._today", lambda: END)
    app = create_app(Settings(_env_file=None))

    def override():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    with session_factory() as s:
        pol, other = Politician(canonical_key="house:a", name="A", chamber="house"), Politician(canonical_key="house:b", name="B", chamber="house")
        xyz, spy, dead = Security(ticker="XYZ"), Security(ticker="SPY"), Security(ticker="DEAD")
        s.add_all([pol, other, xyz, spy, dead])
        s.flush()

        def bars(sec, prices):
            for d, p in prices.items():
                s.add(PriceBar(security_id=sec.id, date=d, close=p, adj_close=p, provider="test"))

        bars(xyz, {date(2026, 7, 1): 100, date(2026, 7, 20): 110, date(2026, 8, 1): 80, date(2026, 8, 10): 90, date(2026, 10, 7): 120})
        bars(spy, {date(2026, 7, 1): 400, date(2026, 7, 20): 420, date(2026, 8, 1): 400, date(2026, 8, 10): 400, date(2026, 10, 7): 440})
        n = 0

        def trade(owner, security, kind, tx, disc):
            nonlocal n
            n += 1
            s.add(Trade(source="t", fingerprint=f"f{n}", politician_id=owner.id, security_id=security.id, politician_name=owner.name, chamber="house",
                        ticker=security.ticker, transaction_type=kind, transaction_date=tx, disclosure_date=disc))

        trade(pol, xyz, "buy", date(2026, 7, 1), date(2026, 7, 20))     # +20% vs SPY +10%; since disclosure +9.09% vs +4.76%
        trade(pol, xyz, "sell", date(2026, 8, 1), date(2026, 8, 10))    # raw +50% vs SPY +10%; since disclosure +33.3% vs +10%
        trade(pol, dead, "buy", date(2026, 9, 1), date(2026, 9, 15))    # no price data at all
        trade(pol, xyz, "buy", date(2025, 1, 2), date(2025, 1, 20))     # more than a year old
        trade(pol, xyz, "buy", date(2026, 9, 20), None)                 # never disclosed
        trade(other, xyz, "buy", date(2026, 7, 1), date(2026, 7, 20))   # someone else's trade must never leak in
        s.commit()
    return TestClient(app)


def get(client, period="6m", basis="transaction", pid=1):
    r = client.get(f"/politicians/{pid}/analytics?period={period}&basis={basis}")
    assert r.status_code == 200, r.text
    return r.json()


def test_six_months_by_trade_date_matches_the_hand_computed_aggregates(client):
    a = get(client, "6m")
    # four trades by trade date; the September buy of a ticker with no prices and the 20 Sept buy (no bar within 7 days of it) are unpriced
    assert (a["trades_in_period"], a["priced"], a["unpriced"], a["benchmark"], a["weighting"]) == (
        4, 2, {"no_prices": 1, "no_price_at_date": 1}, "SPY", "equal")
    assert a["by_type"] == {"buys": 3, "sells": 1, "other": 0}
    raw = a["transaction"]["raw"]
    assert raw["n"] == 2 and raw["n_benchmarked"] == 2
    assert raw["mean_return"] == approx(0.35) and raw["median_return"] == approx(0.35) and raw["mean_benchmark_return"] == approx(0.10)
    assert raw["mean_excess_return"] == approx(0.25) and raw["outperformed"] == 2
    assert raw["best"]["return"] == approx(0.5) and raw["best"]["excess_return"] == approx(0.4) and raw["best"]["ticker"] == "XYZ"


def test_the_since_disclosure_leg_uses_the_disclosure_anchor(client):
    di = get(client, "6m")["disclosure"]["raw"]
    assert di["n"] == 2 and di["mean_return"] == approx((120 / 110 - 1 + 120 / 90 - 1) / 2)
    assert di["mean_benchmark_return"] == approx((440 / 420 - 1 + 440 / 400 - 1) / 2)
    assert di["mean_excess_return"] == approx(((120 / 110 - 1) - (440 / 420 - 1) + (120 / 90 - 1) - (440 / 400 - 1)) / 2)


def test_direction_adjusted_flips_the_sell_and_leaves_the_raw_view_alone(client):
    t = get(client, "6m")["transaction"]
    assert t["raw"]["mean_return"] == approx(0.35)  # buy +20%, sell's raw security return +50%
    assert t["adjusted"]["mean_return"] == approx((0.20 - 0.50) / 2)  # the sell counts as -50%
    assert t["adjusted"]["mean_excess_return"] == approx((0.10 - 0.40) / 2) and t["adjusted"]["outperformed"] == 1
    assert t["adjusted"]["mean_benchmark_return"] is None


def test_shorter_periods_include_only_trades_in_the_window(client):
    a = get(client, "3m")  # starts 2026-07-08: excludes the July 1 buy, includes the August sell and the September ones
    assert a["trades_in_period"] == 3 and a["priced"] == 1
    assert a["transaction"]["raw"]["n"] == 1 and a["transaction"]["raw"]["mean_return"] == approx(0.5)
    assert get(client, "7d")["trades_in_period"] == 0


def test_one_year_excludes_and_all_includes_the_old_trade(client):
    one, everything = get(client, "1y"), get(client, "all")
    assert one["start"] == "2025-10-08" and one["trades_in_period"] == 4
    assert everything["start"] is None and everything["trades_in_period"] == 5


def test_the_basis_chooses_which_date_selects_trades_and_reports_undated_trades(client):
    by_tx = get(client, "6m", "transaction")
    by_disc = get(client, "6m", "disclosure")
    assert by_tx["undated"] == 0 and by_disc["undated"] == 1  # the never-disclosed trade cannot be placed by disclosure date
    assert by_disc["trades_in_period"] == by_tx["trades_in_period"] - 1


def test_an_empty_period_is_an_empty_result_not_an_error(client):
    a = get(client, "7d")
    assert a["priced"] == 0 and a["transaction"]["raw"]["n"] == 0 and a["transaction"]["raw"]["mean_return"] is None
    assert a["transaction"]["raw"]["best"] is None


def test_other_politicians_trades_are_isolated(client):
    assert get(client, "6m", pid=2)["transaction"]["raw"]["n"] == 1
    assert get(client, "6m", pid=1)["transaction"]["raw"]["n"] == 2


def test_unknown_politician_and_invalid_parameters_are_rejected(client):
    assert client.get("/politicians/999/analytics").status_code == 404
    assert client.get("/politicians/1/analytics?period=2w").status_code == 422
    assert client.get("/politicians/1/analytics?basis=x").status_code == 422
