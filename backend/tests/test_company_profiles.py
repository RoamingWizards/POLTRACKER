"""SEC EDGAR company-profile provider: ticker list parsing, SIC normalization, retries and malformed responses. No network."""

import json

import httpx
import pytest

from poltracker.providers.base import ProviderError, ProviderRateLimited
from poltracker.providers.company_profiles import SecEdgarProvider, sic_division, ticker_variants

from conftest import FIXTURES

FX = FIXTURES / "sec"
UA = "Test Agent test@example.com"


def fx(name):
    return json.loads((FX / name).read_text())


def submissions(sic="3721", desc="Aircraft", name="LOCKHEED MARTIN CORP", exchanges=("NYSE",)):
    return {"cik": "0000936468", "name": name, "sic": sic, "sicDescription": desc, "exchanges": list(exchanges), "tickers": ["LMT"]}


def provider(routes, **kw):
    seen = []

    def handler(req):
        seen.append(req)
        for suffix, r in routes.items():
            if str(req.url).endswith(suffix):
                r = r(req) if callable(r) else r
                return r if isinstance(r, httpx.Response) else httpx.Response(200, json=r)
        return httpx.Response(404)

    kw.setdefault("sleep", lambda _s: None)
    kw.setdefault("min_interval", 0)
    p = SecEdgarProvider(UA, client=httpx.Client(headers={"User-Agent": UA}, transport=httpx.MockTransport(handler)), **kw)
    p.seen = seen
    return p


TICKERS = "company_tickers_exchange.json"


def routes(**extra):
    return {TICKERS: fx("company_tickers_exchange.json"), "CIK0000320193.json": fx("submissions_aapl.json"),
            "CIK0000936468.json": submissions(), "CIK0001067983.json": submissions("6331", "Fire, Marine & Casualty Insurance", "BERKSHIRE HATHAWAY INC"),
            "CIK0001000003.json": submissions("", "", "NO SIC TRUST"), **extra}


# --- SIC -> division (official grouping) ----------------------------------------------------------------------

@pytest.mark.parametrize("sic,division", [
    ("0100", "Agriculture, Forestry, and Fishing"), ("1311", "Mining"), ("1531", "Construction"), ("2834", "Manufacturing"), ("3721", "Manufacturing"),
    ("3999", "Manufacturing"), ("4813", "Transportation, Communications, Electric, Gas, and Sanitary Services"), ("5045", "Wholesale Trade"),
    ("5812", "Retail Trade"), ("6021", "Finance, Insurance, and Real Estate"), ("7372", "Services"), ("8071", "Services"), ("9100", "Public Administration"),
])
def test_sic_division_follows_the_published_major_group_ranges(sic, division):
    assert sic_division(sic) == division


@pytest.mark.parametrize("sic", [None, "", "0000", "999", "12345", "abcd", " 371"])
def test_sic_division_is_none_for_missing_or_malformed_codes(sic):
    assert sic_division(sic) is None


@pytest.mark.parametrize("sic", ["1800", "1900", "6800", "9000"])
def test_a_code_in_a_gap_between_the_published_major_groups_has_no_division(sic):
    assert sic_division(sic) is None  # 18-19, 68 and 90 are not SIC major groups; nothing is guessed


def test_ticker_variants_are_exactly_the_given_ticker_and_the_dot_hyphen_swap():
    assert ticker_variants("brk.b") == ["BRK.B", "BRK-B"] and ticker_variants("BRK-B") == ["BRK-B", "BRK.B"] and ticker_variants("AAPL") == ["AAPL"]


# --- the provider ---------------------------------------------------------------------------------------------

def test_a_listed_ticker_gets_cik_sic_industry_division_exchange_and_official_name():
    p = provider(routes())
    p.prepare(["AAPL"])
    prof = p.get_profile("aapl")
    assert (prof.ticker, prof.company_name, prof.cik, prof.sic_code, prof.industry, prof.sector, prof.exchange) == (
        "AAPL", "Apple Inc.", "0000320193", "3571", "Electronic Computers", "Manufacturing", "Nasdaq")
    assert prof.source == "sec-edgar" and prof.source_url == "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193"


def test_requests_are_one_ticker_list_plus_one_submission_per_security_with_the_user_agent():
    p = provider(routes())
    p.prepare(["AAPL", "LMT"])
    p.get_profile("AAPL"), p.get_profile("LMT")
    assert p.requests_made == 3 and len(p.seen) == 3
    assert all(r.headers["user-agent"] == UA for r in p.seen)
    assert str(p.seen[1].url) == "https://data.sec.gov/submissions/CIK0000320193.json"


def test_class_shares_resolve_through_the_deterministic_dot_to_hyphen_rule():
    p = provider(routes())
    p.prepare([])
    prof = p.get_profile("BRK.B")  # POLTRACKER's spelling; the SEC lists BRK-B
    assert prof.cik == "0001067983" and prof.ticker == "BRK.B" and prof.industry == "Fire, Marine & Casualty Insurance"


def test_an_unlisted_ticker_is_none_and_no_fuzzy_name_matching_is_attempted():
    p = provider(routes())
    p.prepare([])
    assert p.get_profile("SPY") is None and p.get_profile("APPLE") is None and p.get_profile("AAP") is None
    assert p.requests_made == 1  # only the ticker list; nothing was looked up for non-matches


def test_a_ticker_listed_under_two_ciks_is_never_resolved():
    p = provider(routes())
    p.prepare([])
    assert p.get_profile("DUAL") is None and p.is_ambiguous("DUAL")


def test_a_company_without_a_sic_code_is_returned_without_industry_or_sector():
    p = provider(routes())
    p.prepare([])
    prof = p.get_profile("NOSIC")
    assert (prof.cik, prof.sic_code, prof.industry, prof.sector) == ("0001000003", None, None, None)


def test_missing_submission_fields_do_not_break_the_profile():
    p = provider(routes(**{"CIK0000936468.json": {"sic": 3721}}))  # a numeric sic, no name, no exchanges
    p.prepare([])
    prof = p.get_profile("LMT")
    assert (prof.company_name, prof.sic_code, prof.industry, prof.exchange) == ("LOCKHEED MARTIN CORP", "3721", None, "NYSE")


@pytest.mark.parametrize("body", [{"data": []}, {"fields": ["cik"], "data": []}, {"fields": "x", "data": []}, [1, 2]])
def test_a_malformed_ticker_list_is_a_provider_error(body):
    with pytest.raises(ProviderError):
        provider({TICKERS: body}).prepare([])


def test_non_json_responses_are_provider_errors():
    with pytest.raises(ProviderError, match="not JSON"):
        provider({TICKERS: httpx.Response(200, content=b"<html>")}).prepare([])


def test_a_submission_that_404s_is_a_provider_error_for_that_security_only():
    p = provider({TICKERS: fx("company_tickers_exchange.json")})
    p.prepare([])
    with pytest.raises(ProviderError, match="404"):
        p.get_profile("AAPL")


def test_transient_errors_are_retried_with_backoff_then_succeed():
    calls, sleeps = [], []

    def flaky(req):
        calls.append(1)
        return httpx.Response([500, 429, 200][len(calls) - 1], json=fx("company_tickers_exchange.json"))

    p = provider({TICKERS: flaky}, sleep=sleeps.append)
    p.prepare([])
    assert len(calls) == 3 and sleeps == [2, 4]


def test_a_persistent_rate_limit_raises_the_dedicated_error_mentioning_the_user_agent():
    with pytest.raises(ProviderRateLimited, match="SEC_USER_AGENT"):
        provider({TICKERS: httpx.Response(403, text="Request Rate Threshold Exceeded")}, max_retries=1).prepare([])


def test_requests_are_paced_at_the_configured_interval():
    sleeps, ticks = [], iter(range(1000))
    p = provider(routes(), min_interval=0.15, sleep=sleeps.append, clock=lambda: next(ticks) * 0.01)
    p.prepare([])
    p.get_profile("AAPL"), p.get_profile("LMT")
    assert sleeps and all(0 < s <= 0.15 for s in sleeps)


def test_a_network_error_is_a_provider_error_without_the_url_query():
    def boom(req):
        raise httpx.ConnectError("down", request=req)

    with pytest.raises(ProviderError, match="network error"):
        provider({TICKERS: boom}, max_retries=0).prepare([])
