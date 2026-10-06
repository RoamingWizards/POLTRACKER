from collections import Counter

import pytest
from fastapi.testclient import TestClient

from poltracker.api.main import app, get_session
from poltracker.ingest import store_trades
from poltracker.providers.congressinvests import normalize_record


@pytest.fixture
def client(session_factory, recent_body):
    trades = [normalize_record(r) for r in recent_body["trades"]]
    with session_factory() as s:
        store_trades(s, trades, Counter())
        s.commit()

    def override():
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_and_get_trade(client):
    body = client.get("/trades", params={"limit": 5}).json()
    assert body["total"] == 25 and len(body["items"]) == 5
    one = client.get(f"/trades/{body['items'][0]['id']}")
    assert one.status_code == 200
    assert client.get("/trades/999999").status_code == 404


def test_trade_filters(client):
    body = client.get("/trades", params={"ticker": "jnj"}).json()
    assert body["total"] >= 1 and all(t["ticker"] == "JNJ" for t in body["items"])
    assert client.get("/trades", params={"chamber": "mars"}).status_code == 422


def test_politicians_and_security(client):
    pols = client.get("/politicians", params={"q": "doggett"}).json()
    assert pols["total"] == 1
    pid = pols["items"][0]["id"]
    detail = client.get(f"/politicians/{pid}").json()
    assert detail["trade_count"] >= 1
    sec = client.get("/securities/jnj").json()
    assert sec["ticker"] == "JNJ" and sec["recent_trades"]
    assert client.get("/securities/NOPE").status_code == 404


def test_prices_and_performance_endpoints(client, session_factory):
    from datetime import date, timedelta

    from poltracker.models import PriceBar, Security
    from sqlalchemy import select

    # Give JNJ and SPY a short price history around the fixture's 2026-09-08 trade.
    with session_factory() as s:
        spy = Security(ticker="SPY", name="SPY")
        s.add(spy)
        jnj = s.scalar(select(Security).where(Security.ticker == "JNJ"))
        s.flush()
        d = date(2026, 9, 7)
        for i in range(30):
            day = d + timedelta(days=i)
            if day.weekday() < 5:
                for sec, base in ((jnj, 100.0), (spy, 400.0)):
                    p = base + i
                    s.add(PriceBar(security_id=sec.id, date=day, open=p, high=p, low=p, close=p, adj_close=p, volume=1, provider="t"))
        jnj.price_status, jnj.price_from, jnj.price_to = "ok", d, d + timedelta(days=29)
        s.commit()

    prices = client.get("/securities/jnj/prices", params={"start": "2026-09-08", "end": "2026-09-10"}).json()
    assert [b["date"] for b in prices["bars"]] == ["2026-09-08", "2026-09-09", "2026-09-10"]
    assert prices["price_status"] == "ok"

    perf = client.get("/securities/JNJ/performance").json()
    assert perf["benchmark"] == "SPY" and perf["total"] >= 1
    item = perf["items"][0]
    assert item["trade"]["ticker"] == "JNJ"
    p = item["performance"]
    assert p["status"] == "ok"
    assert p["transaction"]["anchor_date"] == "2026-09-08"
    assert p["transaction"]["return"] is not None and p["transaction"]["excess_return"] is not None
    assert "transaction_return" in p["direction_adjusted"]

    assert client.get("/securities/NOPE/prices").status_code == 404
    assert client.get("/securities/NOPE/performance").status_code == 404


def test_trade_sorting(client):
    asc = client.get("/trades", params={"sort_by": "transaction_date", "order": "asc", "limit": 500}).json()["items"]
    dates = [t["transaction_date"] for t in asc]
    assert dates == sorted(dates)
    desc = client.get("/trades", params={"sort_by": "ticker", "order": "desc", "limit": 500}).json()["items"]
    tickers = [t["ticker"] or "" for t in desc]
    assert tickers == sorted(tickers, reverse=True)
    assert client.get("/trades", params={"sort_by": "password"}).status_code == 422


def test_overview_endpoint(client):
    body = client.get("/stats/overview", params={"days": 365}).json()
    assert body["totals"]["trades"] == 25
    assert body["totals"]["trades_in_window"] + 0 <= 25
    assert len(body["daily"]) == 366 and sum(d["count"] for d in body["daily"]) == body["totals"]["trades_in_window"]
    assert body["top_tickers"] and body["top_politicians"]
    assert sum(m["buys"] + m["sells"] + m["other"] for m in body["monthly"]) == 25


def test_status_endpoint(client):
    body = client.get("/status").json()
    assert body["trades_total"] == 25 and body["trades_by_source"] == {"congressinvests": 25}
    assert body["securities_pending"] == body["securities_total"] > 0
    assert body["invalid_date_trades"] == 0 and body["benchmark_ticker"] == "SPY"
