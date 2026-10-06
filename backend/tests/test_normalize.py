import pytest

from poltracker.normalize import (
    clean_asset_name,
    normalize_name,
    normalize_ticker,
    normalize_transaction_type,
    parse_amount,
    politician_key,
)
from poltracker.providers.congressinvests import normalize_record


@pytest.mark.parametrize(
    "text, expected",
    [
        ("$1,001 - $15,000", (1001, 15000)),
        ("$15,001 - $50,000", (15001, 50000)),
        ("$1,000,001 - $5,000,000", (1000001, 5000000)),
        ("$50,000,001 - $100,000,000", (50000001, 100000000)),
        ("Over $50,000,000", (50000000, None)),
        ("$15,000", (15000, 15000)),
        ("$15,000 - $1,001", (1001, 15000)),
        ("", (None, None)),
        (None, (None, None)),
        ("Unknown", (None, None)),
    ],
)
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected


def test_normalize_name_strips_honorifics():
    assert normalize_name("John J Mr McGuire") == "John J McGuire"
    assert normalize_name("Hon. Nancy  Pelosi") == "Nancy Pelosi"
    assert normalize_name("Steve Cohen") == "Steve Cohen"


def test_politician_key_is_chamber_scoped_and_punctuation_blind():
    assert politician_key("Steve Cohen", "house") == politician_key("steve  cohen", "house")
    assert politician_key("Steve Cohen", "house") != politician_key("Steve Cohen", "senate")


@pytest.mark.parametrize(
    "raw, expected",
    [("nvda", "NVDA"), (" BRK.B ", "BRK.B"), ("--", None), ("", None), (None, None), ("N/A", None), ("bad ticker!", None)],
)
def test_normalize_ticker(raw, expected):
    assert normalize_ticker(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [("buy", "buy"), ("Purchase", "buy"), ("sell", "sell"), ("Sale (Partial)", "sell_partial"), ("exchange", "exchange"), ("???", "unknown"), (None, "unknown")],
)
def test_normalize_transaction_type(raw, expected):
    assert normalize_transaction_type(raw) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Johnson & Johnson Common Stock P 09/08/2026 10/05/2026 $1,001 - $15,000", "Johnson & Johnson Common Stock"),
        ("Home Depot, Inc. (HD) [ST] P 09/17/2026 10/05/2026 $1,001 - $15,000", "Home Depot, Inc."),
        ("NVIDIA Corporation - Common Stock (NVDA) [ST]", "NVIDIA Corporation - Common Stock"),
        (None, None),
        ("", None),
    ],
)
def test_clean_asset_name(raw, expected):
    assert clean_asset_name(raw) == expected


def test_normalize_real_fixture_records(recent_body):
    trades = [normalize_record(r) for r in recent_body["trades"]]
    assert all(t is not None for t in trades)
    first = trades[0]
    assert (first.politician_name, first.chamber, first.ticker) == ("Lloyd Doggett", "house", "JNJ")
    assert first.transaction_type == "buy"
    assert (first.amount_min, first.amount_max) == (1001, 15000)
    assert first.disclosure_date.isoformat() == "2026-10-05"
    assert first.source_url.endswith(".pdf")


def test_normalize_record_rejects_unusable():
    assert normalize_record({"member": "", "chamber": "House", "tx_date": "2026-01-01"}) is None
    assert normalize_record({"member": "A B", "chamber": "Mars", "tx_date": "2026-01-01"}) is None
    assert normalize_record({"member": "A B", "chamber": "House", "tx_date": "garbage"}) is None
