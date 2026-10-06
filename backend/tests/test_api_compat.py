"""Behaviour that must be identical on SQLite and PostgreSQL (run with POLTRACKER_TEST_DATABASE_URL to check both)."""

from collections import Counter
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from poltracker.api.main import app, get_session
from poltracker.config import get_settings
from poltracker.domain import TradeIn
from poltracker.ingest import store_trades
from poltracker.models import IngestState

TODAY = date.today()


def trade(name="Jane Doe", ticker="AAPL", asset="Apple Inc.", disclosed: date | None = TODAY - timedelta(days=5),
          amin=1001, amax=15000, kind="buy", tx=None, chamber="house") -> TradeIn:
    return TradeIn(
        source="congressinvests", politician_name=name, chamber=chamber, transaction_type=kind,
        transaction_date=tx or TODAY - timedelta(days=10), ticker=ticker, asset_name=asset,
        disclosure_date=disclosed, amount_min=amin, amount_max=amax,
    )


@pytest.fixture
def api(session_factory):
    def override():
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app), session_factory
    app.dependency_overrides.clear()


def load(factory, trades):
    with factory() as s:
        store_trades(s, trades, Counter())
        s.commit()


# ── NULL ordering ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("order, expected", [("asc", ["AAA", "BBB", None]), ("desc", ["BBB", "AAA", None])])
def test_null_tickers_sort_last_in_both_directions(api, order, expected):
    client, factory = api
    load(factory, [trade(ticker="BBB", asset="B"), trade(ticker=None, asset="Treasury bill"), trade(ticker="AAA", asset="A")])
    items = client.get("/trades", params={"sort_by": "ticker", "order": order}).json()["items"]
    assert [t["ticker"] for t in items] == expected


@pytest.mark.parametrize("order", ["asc", "desc"])
def test_null_amounts_and_dates_sort_last(api, order):
    client, factory = api
    load(factory, [
        trade(ticker="A1", amin=None, amax=None),
        trade(ticker="B1", amin=1001, amax=15000, disclosed=None),
        trade(ticker="C1", amin=50001, amax=100000),
    ])
    by_amount = client.get("/trades", params={"sort_by": "amount_min", "order": order}).json()["items"]
    assert by_amount[-1]["amount_min"] is None
    by_disclosure = client.get("/trades", params={"sort_by": "disclosure_date", "order": order}).json()["items"]
    assert by_disclosure[-1]["disclosure_date"] is None


def test_security_recent_trades_put_undisclosed_last(api):
    client, factory = api
    load(factory, [trade(disclosed=None), trade(disclosed=TODAY - timedelta(days=3), amin=15001, amax=50000)])
    recent = client.get("/securities/AAPL").json()["recent_trades"]
    assert recent[0]["disclosure_date"] is not None and recent[-1]["disclosure_date"] is None


# ── text ordering is byte order everywhere ───────────────────────────────────

NAMES = ["adam lower", "Zed Upper", "Mario Díaz-Balart", "A. Mitchell McConnell Jr.", "Adam B Schiff", "Mario Diaz"]


def test_politician_names_sort_by_bytes(api):
    client, factory = api
    load(factory, [trade(name=n, ticker=f"T{i}", asset=f"A{i}") for i, n in enumerate(NAMES)])
    got = [p["name"] for p in client.get("/politicians").json()["items"]]
    assert got == sorted(NAMES, key=lambda n: n.encode())  # not a locale order: 'Zed' before 'adam'


def test_trade_sort_by_politician_name_is_byte_order(api):
    client, factory = api
    load(factory, [trade(name=n, ticker=f"T{i}", asset=f"A{i}") for i, n in enumerate(NAMES)])
    got = [t["politician_name"] for t in client.get("/trades", params={"sort_by": "politician_name", "order": "asc"}).json()["items"]]
    assert got == sorted(NAMES, key=lambda n: n.encode())


# ── overview: deterministic names and tie-breaks ─────────────────────────────


def test_top_ticker_name_comes_from_the_security_not_max_of_trade_names(api):
    client, factory = api
    # max() over these strings picks the longer, noisier one; the stored security name is the first clean one.
    load(factory, [
        trade(ticker="UNH", asset="UnitedHealth Group Incorporated"),
        trade(ticker="UNH", asset="UnitedHealth Group Incorporated S (partial) 06/12/2026", amin=15001, amax=50000),
    ])
    top = client.get("/stats/overview").json()["top_tickers"]
    assert top[0]["ticker"] == "UNH" and top[0]["name"] == "UnitedHealth Group Incorporated"


def test_overview_ties_break_on_creation_order_not_text(api):
    client, factory = api
    load(factory, [trade(ticker="ZZZ", asset="Z"), trade(ticker="AAA", asset="A"), trade(ticker="MMM", asset="M")])
    assert [t["ticker"] for t in client.get("/stats/overview").json()["top_tickers"]] == ["ZZZ", "AAA", "MMM"]


# ── stale ingestion ──────────────────────────────────────────────────────────


def set_last_success(factory, when: datetime | None):
    with factory() as s:
        s.merge(IngestState(source="congressinvests", backfill_complete=True, last_success_at=when))
        s.commit()


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def test_fresh_ingestion_is_not_stale(api):
    client, factory = api
    set_last_success(factory, utcnow() - timedelta(hours=1))
    body = client.get("/status").json()
    assert body["ingest_stale"] is False
    assert 0.9 < body["ingest_age_hours"] < 1.2
    assert body["ingest_stale_after_hours"] == 24 and body["last_successful_ingest_at"] is not None


def test_old_ingestion_is_stale(api):
    client, factory = api
    set_last_success(factory, utcnow() - timedelta(hours=30))
    body = client.get("/status").json()
    assert body["ingest_stale"] is True and body["ingest_age_hours"] > 29


def test_never_recorded_counts_as_stale(api):
    client, _ = api
    body = client.get("/status").json()
    assert body["ingest_stale"] is True and body["last_successful_ingest_at"] is None and body["ingest_age_hours"] is None


def test_quiet_days_do_not_cause_a_false_warning(api):
    """Old trades but a recent successful run (a day with no new disclosures) must not warn."""
    client, factory = api
    load(factory, [trade()])
    set_last_success(factory, utcnow() - timedelta(minutes=20))
    assert client.get("/status").json()["ingest_stale"] is False


def test_threshold_is_configurable(api, monkeypatch):
    client, factory = api
    set_last_success(factory, utcnow() - timedelta(hours=30))
    monkeypatch.setenv("INGEST_STALE_AFTER_HOURS", "48")
    get_settings.cache_clear()
    try:
        body = client.get("/status").json()
        assert body["ingest_stale"] is False and body["ingest_stale_after_hours"] == 48
    finally:
        get_settings.cache_clear()
