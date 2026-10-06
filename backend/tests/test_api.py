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
