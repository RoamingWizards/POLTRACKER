"""SQLite and PostgreSQL must give the same API answers for the same data.

Skipped unless POLTRACKER_TEST_DATABASE_URL is set (the database name must contain "test").
To also reproduce Linux-style locale collation, point it at a database created with an ICU locale:
    CREATE DATABASE poltracker_test_icu LOCALE_PROVIDER icu ICU_LOCALE 'en-US' TEMPLATE template0;
"""

from collections import Counter
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from poltracker.api.main import app, get_session
from poltracker.domain import TradeIn
from poltracker.ingest import store_trades
from poltracker.models import PriceBar, Security

TODAY = date.today()

# Names chosen to expose locale collation: case, punctuation, accents, lowercase leading letters.
NAMES = [
    ("A. Mitchell McConnell Jr.", "senate"), ("Adam B Schiff", "senate"), ("Alan Armstrong", "senate"),
    ("Mario Díaz-Balart", "house"), ("Mario Diaz", "house"), ("Nydia M. Velázquez", "house"),
    ("Zed Upper", "house"), ("adam lower", "house"), ("McArthur Smith", "house"), ("Mcarthur Jones", "house"),
    ("Jean-Luc Picard", "house"), ("Jean Luc Picard", "house"), ("O'Brien Miles", "house"),
]
TICKERS = ["AAPL", "BRK.B", "BRK-B", "BRKB", "aa", "AA", "A", "SPYX", None, "MSFT"]


def dataset() -> list[TradeIn]:
    out = []
    for i in range(120):
        name, chamber = NAMES[i % len(NAMES)]
        ticker = TICKERS[i % len(TICKERS)]
        out.append(
            TradeIn(
                source="congressinvests", politician_name=name, chamber=chamber,
                transaction_type=("buy", "sell", "sell_partial", "exchange")[i % 4],
                transaction_date=TODAY - timedelta(days=3 + i % 50), ticker=ticker,
                asset_name=f"Asset {ticker or 'none'} {i % 3}" if ticker else "Treasury bill",
                disclosure_date=None if i % 17 == 0 else TODAY - timedelta(days=1 + i % 30),
                amount_min=None if i % 13 == 0 else (1001, 15001, 50001)[i % 3],
                amount_max=None if i % 13 == 0 else (15000, 50000, 100000)[i % 3],
                source_url=f"https://example.test/{i}.pdf",
            )
        )
    return out


def populate(factory):
    with factory() as s:
        store_trades(s, dataset(), Counter())
        s.commit()
    with factory() as s:
        spy = Security(ticker="SPY", name="SPY")
        s.add(spy)
        s.flush()
        for sec in [spy] + [x for x in s.query(Security).filter(Security.ticker.in_(["AAPL", "MSFT"]))]:
            sec.price_status, sec.price_from, sec.price_to = "ok", TODAY - timedelta(days=80), TODAY
            for d in range(80):
                day = TODAY - timedelta(days=80 - d)
                if day.weekday() < 5:
                    p = 100 + d * (1.1 if sec.ticker != "SPY" else 0.4)
                    s.add(PriceBar(security_id=sec.id, date=day, open=p, high=p, low=p, close=p, adj_close=p, volume=1, provider="t"))
        s.commit()


def paths() -> list[str]:
    out = ["/trades?limit=500", "/trades/1", "/trades/77", "/politicians?limit=500", "/politicians?q=mario&limit=50",
           "/politicians?chamber=senate", "/politicians/1", "/stats/overview?days=30", "/stats/overview?days=365",
           "/securities/AAPL", "/securities/AAPL/prices", "/securities/AAPL/performance", "/securities/MSFT/performance",
           "/securities/NOPE", "/trades?ticker=brk.b", "/trades?chamber=house&transaction_type=sell&limit=500",
           "/trades?date_from=%s&date_to=%s&limit=500" % (TODAY - timedelta(days=20), TODAY - timedelta(days=5))]
    for field in ("transaction_date", "disclosure_date", "amount_min", "ticker", "politician_name"):
        for order in ("asc", "desc"):
            out.append(f"/trades?sort_by={field}&order={order}&limit=500")
            out.append(f"/trades?sort_by={field}&order={order}&limit=25&offset=25")
    return out


VOLATILE = {"last_ingested_at", "last_successful_ingest_at", "ingest_age_hours"}


def fetch_all(factory):
    def override():
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    try:
        client = TestClient(app)
        out = {}
        for p in paths() + ["/status"]:
            r = client.get(p)
            body = r.json()
            if p == "/status":
                body = {k: v for k, v in body.items() if k not in VOLATILE}
            out[p] = (r.status_code, body)
        return out
    finally:
        app.dependency_overrides.clear()


def test_every_endpoint_matches_across_databases(sqlite_session_factory, pg_session_factory):
    populate(sqlite_session_factory)
    populate(pg_session_factory)
    lite, pg = fetch_all(sqlite_session_factory), fetch_all(pg_session_factory)
    differing = [p for p in lite if lite[p] != pg[p]]
    assert not differing, f"{len(differing)} endpoints differ between SQLite and PostgreSQL: {differing[:5]}"
    assert len(lite) >= 35  # the comparison actually covered a meaningful surface
