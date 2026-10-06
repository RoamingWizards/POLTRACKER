from collections import Counter
from datetime import date, timedelta

from sqlalchemy import func, select

from poltracker.domain import TradeIn
from poltracker.ingest import store_trades
from poltracker.models import PriceBar, Security
from poltracker.prices import refresh_prices
from poltracker.providers.prices import PriceBarIn, PriceProvider, PriceProviderError

TODAY = date(2026, 1, 15)
HOLIDAYS = {date(2025, 11, 27), date(2025, 12, 25), date(2026, 1, 1)}


def days(start: date, end: date):
    d = start
    while d <= end:
        if d.weekday() < 5 and d not in HOLIDAYS:
            yield d
        d += timedelta(days=1)


def bar(d: date, price: float, adj: float | None = None) -> PriceBarIn:
    return PriceBarIn(d, price, price, price, price, adj if adj is not None else price, 1000)


class FakePrices(PriceProvider):
    name = "fake"

    def __init__(self, tickers: dict[str, float], through: date = date(2026, 1, 14)):
        self.history = {t: [bar(d, base + i) for i, d in enumerate(days(date(2025, 10, 1), through))] for t, base in tickers.items()}
        self.calls: list[tuple[list[str], date, date]] = []
        self.fail = False

    def fetch_daily(self, tickers, start, end):
        self.calls.append((list(tickers), start, end))
        if self.fail:
            raise PriceProviderError("boom")
        return {t: [b for b in self.history[t] if start <= b.date <= end] for t in tickers if t in self.history}


def trade(ticker, tx, disc=None, **kw) -> TradeIn:
    return TradeIn(
        source="t", politician_name="Jane Doe", chamber="house", transaction_type=kw.get("kind", "buy"),
        transaction_date=tx, ticker=ticker, asset_name=ticker, disclosure_date=disc or tx + timedelta(days=10),
        amount_min=1001, amount_max=15000,
    )


def seed(session_factory, trades: list[TradeIn]) -> None:
    with session_factory() as s:
        store_trades(s, trades, Counter())
        s.commit()


def run(provider, session_factory, today=TODAY, **kw):
    return refresh_prices(provider, session_factory, today=today, **kw)


def bar_count(session_factory, ticker) -> int:
    with session_factory() as s:
        return s.scalar(select(func.count()).select_from(PriceBar).join(Security).where(Security.ticker == ticker))


def security(session_factory, ticker) -> Security:
    with session_factory() as s:
        return s.scalar(select(Security).where(Security.ticker == ticker))


def test_prices_are_fetched_stored_and_spy_included(session_factory):
    seed(session_factory, [trade("AAA", date(2025, 11, 3)), trade("BBB", date(2025, 12, 1))])
    prov = FakePrices({"AAA": 10, "BBB": 20, "SPY": 400})
    r = run(prov, session_factory)
    assert r.enriched == 3 and not r.failed and not r.unavailable
    assert len(prov.calls) == 1  # one batched call for everything
    assert set(prov.calls[0][0]) == {"AAA", "BBB", "SPY"}
    assert bar_count(session_factory, "AAA") > 40 and bar_count(session_factory, "SPY") > 40
    spy = security(session_factory, "SPY")
    assert spy.price_status == "ok" and spy.price_from == date(2025, 11, 3) and spy.price_to == TODAY


def test_second_run_is_fully_cached_and_makes_no_calls(session_factory):
    seed(session_factory, [trade("AAA", date(2025, 11, 3))])
    prov = FakePrices({"AAA": 10, "SPY": 400})
    run(prov, session_factory)
    prov.calls.clear()
    r = run(prov, session_factory)
    assert prov.calls == []
    assert r.cached == 2 and r.enriched == 0


def test_next_day_fetches_only_the_tail(session_factory):
    seed(session_factory, [trade("AAA", date(2025, 11, 3))])
    prov = FakePrices({"AAA": 10, "SPY": 400}, through=date(2026, 1, 16))
    run(prov, session_factory)
    before = bar_count(session_factory, "AAA")
    prov.calls.clear()
    run(prov, session_factory, today=TODAY + timedelta(days=1), overlap_days=3)
    assert len(prov.calls) == 1
    _, start, end = prov.calls[0]
    assert start == TODAY - timedelta(days=3) and end == TODAY + timedelta(days=1)  # not the whole history
    assert bar_count(session_factory, "AAA") == before + 1  # 2026-01-15 added, no duplicates


def test_older_trade_extends_only_the_head(session_factory):
    seed(session_factory, [trade("AAA", date(2025, 12, 1))])
    prov = FakePrices({"AAA": 10, "SPY": 400})
    run(prov, session_factory)
    prov.calls.clear()
    seed(session_factory, [trade("AAA", date(2025, 11, 3))])
    run(prov, session_factory)
    assert len(prov.calls) == 1
    _, start, end = prov.calls[0]
    assert (start, end) == (date(2025, 11, 3), date(2025, 12, 1))
    assert security(session_factory, "AAA").price_from == date(2025, 11, 3)


def test_bars_are_not_duplicated_by_overlapping_fetches(session_factory):
    seed(session_factory, [trade("AAA", date(2025, 12, 1))])
    prov = FakePrices({"AAA": 10, "SPY": 400}, through=date(2026, 1, 16))
    run(prov, session_factory)
    run(prov, session_factory, today=TODAY + timedelta(days=1))
    with session_factory() as s:
        dupes = s.execute(
            select(PriceBar.security_id, PriceBar.date, func.count()).group_by(PriceBar.security_id, PriceBar.date).having(func.count() > 1)
        ).all()
    assert dupes == []


def test_dead_ticker_is_marked_unavailable_and_not_refetched(session_factory):
    seed(session_factory, [trade("DEAD", date(2025, 11, 3)), trade("AAA", date(2025, 11, 3))])
    prov = FakePrices({"AAA": 10, "SPY": 400})
    r = run(prov, session_factory)
    assert r.unavailable == ["DEAD"] and r.enriched == 2
    assert security(session_factory, "DEAD").price_status == "unavailable"
    prov.calls.clear()
    r2 = run(prov, session_factory)
    assert r2.deferred == ["DEAD"] and prov.calls == []


def test_unavailable_ticker_is_retried_after_the_window(session_factory):
    seed(session_factory, [trade("DEAD", date(2025, 11, 3)), trade("AAA", date(2025, 11, 3))])
    prov = FakePrices({"AAA": 10, "SPY": 400})
    run(prov, session_factory)
    with session_factory() as s:
        sec = s.scalar(select(Security).where(Security.ticker == "DEAD"))
        sec.price_checked_at -= timedelta(days=8)
        s.commit()
    prov.calls.clear()
    run(prov, session_factory, retry_days=7)
    assert any("DEAD" in tickers for tickers, _, _ in prov.calls)


def test_provider_failure_does_not_poison_the_cache(session_factory):
    seed(session_factory, [trade("AAA", date(2025, 11, 3))])
    prov = FakePrices({"AAA": 10, "SPY": 400})
    prov.fail = True
    r = run(prov, session_factory)
    assert set(r.failed) == {"AAA", "SPY"} and r.unavailable == []
    assert security(session_factory, "AAA").price_status is None
    prov.fail = False
    assert run(prov, session_factory).enriched == 2  # recovers next run


def test_all_empty_large_batch_is_treated_as_failure_not_dead_tickers(session_factory):
    seed(session_factory, [trade(t, date(2025, 11, 3)) for t in ("AAA", "BBB", "CCC")])
    prov = FakePrices({})  # provider silently returns nothing (e.g. rate limited)
    r = run(prov, session_factory)
    assert r.unavailable == [] and len(r.failed) == 4
    assert security(session_factory, "AAA").price_status is None


def test_invalid_future_date_trade_is_reported_and_not_priced(session_factory):
    bad = trade("SONY", date(2026, 12, 26), disc=date(2026, 2, 9))
    good = trade("AAA", date(2025, 11, 3))
    seed(session_factory, [bad, good])
    prov = FakePrices({"AAA": 10, "SONY": 5, "SPY": 400})
    r = run(prov, session_factory, today=date(2026, 1, 15))
    assert [t for _, t, _ in r.invalid_date_trades] == ["SONY"]
    assert r.no_valid_dates == ["SONY"]
    assert all("SONY" not in tickers for tickers, _, _ in prov.calls)  # no network spent on it
    with session_factory() as s:
        from poltracker.models import Trade
        original = s.scalar(select(Trade).where(Trade.ticker == "SONY"))
    assert original.transaction_date == date(2026, 12, 26)  # source date preserved


def test_restated_adjusted_close_triggers_full_history_rebuild(session_factory):
    seed(session_factory, [trade("AAA", date(2025, 11, 3))])
    prov = FakePrices({"AAA": 10, "SPY": 400}, through=date(2026, 1, 16))
    run(prov, session_factory)
    # A dividend restates history: every old adj_close is now 2% lower.
    prov.history["AAA"] = [bar(b.date, b.close, b.adj_close * 0.98) for b in prov.history["AAA"]]
    prov.calls.clear()
    r = run(prov, session_factory, today=TODAY + timedelta(days=1), overlap_days=3)
    assert r.refetched_for_adjustment == ["AAA"]
    assert any(start == date(2025, 11, 3) for _, start, _ in prov.calls)  # whole history re-requested
    with session_factory() as s:
        old = s.scalar(select(PriceBar.adj_close).join(Security).where(Security.ticker == "AAA", PriceBar.date == date(2025, 11, 3)))
    assert old == prov.history["AAA"][[b.date for b in prov.history["AAA"]].index(date(2025, 11, 3))].adj_close
