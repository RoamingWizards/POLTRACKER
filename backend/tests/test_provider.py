"""CongressInvestsProvider over a mocked HTTP transport (no network, no daily-quota spend)."""

import httpx
import pytest
from sqlalchemy import func, select

from poltracker.ingest import ingest_recent
from poltracker.models import Trade
from poltracker.providers import CongressInvestsProvider, ProviderError, ProviderRateLimited


def provider_for(handler) -> CongressInvestsProvider:
    client = httpx.Client(base_url="https://example.test", transport=httpx.MockTransport(handler))
    return CongressInvestsProvider("https://example.test", client=client)


def record(i: int, **kw) -> dict:
    base = {
        "member": f"Member {i}", "chamber": "House", "trade_type": "buy", "amount": "$1,001 - $15,000",
        "tx_date": "2026-09-01", "disclosed": "2026-09-20", "asset": f"Company {i}", "ticker": f"T{i}", "link": "https://x/1.pdf",
    }
    base.update(kw)
    return base


def test_fetches_and_normalizes_a_page(recent_body):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"], seen["params"] = request.url.path, dict(request.url.params)
        return httpx.Response(200, json=recent_body)

    page = provider_for(handler).fetch_recent_page(limit=25, offset=0)
    assert seen["path"] == "/trades/recent" and seen["params"] == {"limit": "25", "offset": "0"}
    assert len(page.trades) == 25 and page.has_more is True and page.total == 5381
    assert page.skipped == 0


def test_unusable_records_are_counted_not_fatal():
    body = {"trades": [record(1), record(2, tx_date="garbage"), record(3, chamber="Mars")], "has_more": False, "total": 3}
    page = provider_for(lambda r: httpx.Response(200, json=body)).fetch_recent_page(limit=10)
    assert len(page.trades) == 1 and page.skipped == 2


def test_api_key_is_sent_as_header_when_configured():
    seen = {}
    client = httpx.Client(
        base_url="https://example.test",
        headers={"X-Api-Key": "k"},
        transport=httpx.MockTransport(lambda r: (seen.update(key=r.headers.get("x-api-key")), httpx.Response(200, json={"trades": []}))[1]),
    )
    CongressInvestsProvider("https://example.test", "k", client=client).fetch_recent_page(limit=1)
    assert seen["key"] == "k"


def test_429_is_a_rate_limit_error():
    with pytest.raises(ProviderRateLimited):
        provider_for(lambda r: httpx.Response(429)).fetch_recent_page(limit=10)


def test_server_error_and_bad_json_are_provider_errors():
    with pytest.raises(ProviderError):
        provider_for(lambda r: httpx.Response(503)).fetch_recent_page(limit=10)
    with pytest.raises(ProviderError):
        provider_for(lambda r: httpx.Response(200, text="<html>not json</html>")).fetch_recent_page(limit=10)


def test_network_failure_is_a_provider_error():
    def boom(request):
        raise httpx.ConnectError("down")

    with pytest.raises(ProviderError):
        provider_for(boom).fetch_recent_page(limit=10)


def test_rate_limit_mid_run_keeps_progress_and_the_next_run_resumes(session_factory):
    """Page 1 succeeds, page 2 hits the daily limit: page 1 stays committed, the run reports why it stopped."""
    state = {"limited": True}

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        if offset == 0:
            return httpx.Response(200, json={"trades": [record(1), record(2)], "has_more": True, "total": 4})
        if state["limited"]:
            return httpx.Response(429)
        return httpx.Response(200, json={"trades": [record(3), record(4)], "has_more": False, "total": 4})

    prov = provider_for(handler)
    first = ingest_recent(prov, session_factory, page_size=2, max_pages=5)
    assert first.inserted == 2 and "provider error" in first.stopped and "limit" in first.stopped
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Trade)) == 2  # not rolled back

    state["limited"] = False
    second = ingest_recent(prov, session_factory, page_size=2, max_pages=5)
    assert second.inserted == 2  # picks up the remainder; the first two are recognised, not duplicated
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Trade)) == 4


# ── last successful ingest (drives the stale warning) ────────────────────────


def last_success(session_factory):
    from poltracker.models import IngestState

    with session_factory() as s:
        state = s.get(IngestState, "congressinvests")
        return state.last_success_at if state else None


def test_a_successful_run_records_when_it_finished(session_factory):
    body = {"trades": [record(1)], "has_more": False, "total": 1}
    ingest_recent(provider_for(lambda r: httpx.Response(200, json=body)), session_factory, page_size=5, max_pages=3)
    assert last_success(session_factory) is not None


def test_a_run_that_finds_nothing_new_still_counts_as_successful(session_factory):
    """Quiet days (no new disclosures) are healthy; only errors should leave the timestamp alone."""
    import time

    body = {"trades": [record(1)], "has_more": False, "total": 1}
    prov = provider_for(lambda r: httpx.Response(200, json=body))
    ingest_recent(prov, session_factory, page_size=5, max_pages=3)
    first = last_success(session_factory)
    time.sleep(0.01)
    result = ingest_recent(prov, session_factory, page_size=5, max_pages=3)
    assert result.inserted == 0 and last_success(session_factory) > first


def test_a_failed_run_does_not_update_the_timestamp(session_factory):
    ok = {"trades": [record(1)], "has_more": False, "total": 1}
    ingest_recent(provider_for(lambda r: httpx.Response(200, json=ok)), session_factory, page_size=5, max_pages=3)
    before = last_success(session_factory)
    result = ingest_recent(provider_for(lambda r: httpx.Response(429)), session_factory, page_size=5, max_pages=3)
    assert "provider error" in result.stopped
    assert last_success(session_factory) == before


def test_a_failed_first_run_records_nothing(session_factory):
    ingest_recent(provider_for(lambda r: httpx.Response(503)), session_factory, page_size=5, max_pages=3)
    assert last_success(session_factory) is None


def test_single_run_exit_code_reflects_provider_failure():
    from poltracker.ingest import IngestResult, exit_code

    assert exit_code(IngestResult(stopped="caught up (page had nothing new)")) == 0
    assert exit_code(IngestResult(stopped="reached max_pages; backfill will resume next run")) == 0
    assert exit_code(IngestResult(stopped="provider error: /trades/recent: daily request limit reached")) == 1
