from collections import Counter
from dataclasses import replace
from datetime import date

from sqlalchemy import func, select

from poltracker.domain import TradeIn
from poltracker.ingest import ingest_recent, store_trades
from poltracker.models import Politician, Security, Trade
from poltracker.normalize import fingerprint
from poltracker.providers.base import CongressProvider, TradePage
from poltracker.providers.congressinvests import normalize_record


def make_trade(**kw) -> TradeIn:
    base = dict(
        source="congressinvests", politician_name="Jane Doe", chamber="house", transaction_type="buy",
        transaction_date=date(2026, 9, 1), ticker="AAPL", asset_name="Apple Inc.",
        disclosure_date=date(2026, 9, 20), amount_min=1001, amount_max=15000, source_url="https://x/1.pdf",
    )
    base.update(kw)
    return TradeIn(**base)


class FakeProvider(CongressProvider):
    name = "fake"

    def __init__(self, pages: list[list[TradeIn]]):
        self.pages, self.calls = pages, 0

    def fetch_recent_page(self, *, limit, offset=0, chamber=None):
        idx = offset // limit
        self.calls += 1
        return TradePage(trades=self.pages[idx], has_more=idx + 1 < len(self.pages))

    def fetch_ticker_page(self, ticker, *, limit, offset=0):
        raise NotImplementedError


def count(session_factory, model) -> int:
    with session_factory() as s:
        return s.scalar(select(func.count()).select_from(model))


def test_fingerprint_is_deterministic_and_ignores_url_and_source():
    a = make_trade()
    b = make_trade(source_url="https://other/amended.pdf", source="other-provider")
    assert fingerprint(a) == fingerprint(b)


def test_fingerprint_changes_with_substantive_fields():
    base = fingerprint(make_trade())
    assert fingerprint(make_trade(amount_max=50000)) != base
    assert fingerprint(make_trade(transaction_type="sell")) != base
    assert fingerprint(make_trade(transaction_date=date(2026, 9, 2))) != base
    assert fingerprint(make_trade(politician_name="John Roe")) != base


def test_occurrence_separates_identical_lines():
    t = make_trade()
    assert fingerprint(t, 0) != fingerprint(t, 1)


def test_identical_lines_in_one_batch_are_both_kept(session_factory):
    with session_factory() as s:
        assert store_trades(s, [make_trade(), make_trade()], Counter()) == 2
        s.commit()
    assert count(session_factory, Trade) == 2


def test_reingesting_same_page_inserts_nothing(session_factory):
    page = [make_trade(), make_trade(ticker="MSFT", asset_name="Microsoft")]
    with session_factory() as s:
        assert store_trades(s, page, Counter()) == 2
        s.commit()
    with session_factory() as s:
        assert store_trades(s, page, Counter()) == 0
        s.commit()
    assert count(session_factory, Trade) == 2
    assert count(session_factory, Politician) == 1
    assert count(session_factory, Security) == 2


def test_incremental_run_stops_when_caught_up(session_factory):
    old = [make_trade(ticker="AAA"), make_trade(ticker="BBB")]
    new = [make_trade(ticker="CCC", disclosure_date=date(2026, 9, 25))]
    # First run: backfill two pages.
    p1 = FakeProvider([old, [make_trade(ticker="DDD")]])
    r1 = ingest_recent(p1, session_factory, page_size=2, max_pages=10)
    assert (r1.inserted, p1.calls) == (3, 2)
    # Second run: one new trade on top, then a known page -> stop after 2 requests, not all pages.
    p2 = FakeProvider([new + old[:1], old[1:] + [make_trade(ticker="DDD")], [make_trade(ticker="ZZZ")]])
    r2 = ingest_recent(p2, session_factory, page_size=2, max_pages=10)
    assert r2.inserted == 1
    assert p2.calls == 2
    assert "caught up" in r2.stopped
    # Third run: nothing new -> a single request.
    p3 = FakeProvider([new + old[:1], [make_trade(ticker="ZZZ")]])
    r3 = ingest_recent(p3, session_factory, page_size=2, max_pages=10)
    assert (r3.inserted, p3.calls) == (0, 1)


def test_unticketed_trade_is_stored_without_security(session_factory):
    with session_factory() as s:
        store_trades(s, [make_trade(ticker=None, asset_name="US Treasury Bill")], Counter())
        s.commit()
    assert count(session_factory, Trade) == 1
    assert count(session_factory, Security) == 0


def test_real_fixture_ingests_once(session_factory, recent_body):
    trades = [normalize_record(r) for r in recent_body["trades"]]
    with session_factory() as s:
        first = store_trades(s, trades, Counter())
        s.commit()
    with session_factory() as s:
        second = store_trades(s, trades, Counter())
        s.commit()
    assert first == len(trades)
    assert second == 0
