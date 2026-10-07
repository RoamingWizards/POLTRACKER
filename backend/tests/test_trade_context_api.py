"""The trade API exposes context additively: existing fields are unchanged and `context` is null until the analyzer has run."""

import pytest
from fastapi.testclient import TestClient

from poltracker.api.main import app, get_session
from test_trade_context import run, seed  # noqa: E402  (pytest puts the tests directory on sys.path)

BASE_FIELDS = {"id", "source", "politician_id", "security_id", "politician_name", "chamber", "party", "state", "ticker", "asset_name", "transaction_type",
               "transaction_date", "disclosure_date", "amount_min", "amount_max", "source_url"}


@pytest.fixture
def client(session_factory):
    def override():
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_context_is_null_before_the_analyzer_runs_and_existing_fields_are_unchanged(session_factory, client):
    ids = seed(session_factory)
    body = client.get("/trades", params={"limit": 50}).json()
    assert body["total"] == 14 and all(BASE_FIELDS <= set(t) and t["context"] is None for t in body["items"])
    assert client.get(f"/trades/{ids['big']}").json()["context"] is None
    assert client.get("/trades", params={"flagged": True}).json()["total"] == 0


def test_context_fields_evidence_and_notice_after_analysis(session_factory, client):
    ids = seed(session_factory, dated_seat=True)
    run(session_factory)
    ctx = client.get(f"/trades/{ids['big']}").json()["context"]
    assert ctx["flagged_for_contextual_review"] is True and ctx["signal_count"] == 3 and ctx["committee_relevance"] is True
    assert ctx["secondary_signal_count"] == 2 and ctx["committee_temporal_status"] == "temporally_verified" and ctx["meets_flag_rule"] is True and ctx["flag_pending_temporal_verification"] is False
    assert ctx["signals"] == {"committee_relevance": True, "trade_size_anomaly": True, "disclosure_delay_signal": True, "excess_return_signal": None}
    assert ctx["trade_size_percentile"] == 100 and ctx["trade_size_sample_size"] == 12 and ctx["disclosure_delay_days"] == 59 and ctx["excess_return"] is None
    assert ctx["context_version"] == "2026.2" and ctx["mapping_version"] == "v1" and "do not establish" in ctx["notice"]
    kinds = {(e["signal_type"], e["evidence_type"]) for e in ctx["evidence"]}
    assert ("committee_relevance", "reviewed_direct_mapping") in kinds and ("disclosure_delay_signal", "metric") in kinds
    direct = next(e for e in ctx["evidence"] if e["evidence_type"] == "reviewed_direct_mapping")
    assert direct["committee_code"] == "AS00" and direct["source_url"] and direct["metadata"]["level"] == "direct" and direct["metadata"]["mapping_version"] == "v1"


def test_the_flagged_filter_returns_only_flagged_trades(session_factory, client):
    ids = seed(session_factory, dated_seat=True)
    run(session_factory)
    body = client.get("/trades", params={"flagged": True}).json()
    assert body["total"] == 1 and body["items"][0]["id"] == ids["big"]
    assert client.get("/trades").json()["total"] == 14  # without the filter, everything


def test_a_trade_without_a_committee_has_unknown_relevance_and_is_never_flagged(session_factory, client):
    ids = seed(session_factory)
    run(session_factory)
    other = client.get("/trades", params={"politician_id": ids["other_pol"]}).json()["items"][0]["context"]
    assert other["committee_relevance"] is None and other["committee_relevance_reason"] == "no_committee_assignments" and other["flagged_for_contextual_review"] is False


def test_a_snapshot_only_seat_shows_the_match_but_marks_the_flag_as_pending_verification(session_factory, client):
    ids = seed(session_factory)  # no seat start date
    run(session_factory)
    ctx = client.get(f"/trades/{ids['big']}").json()["context"]
    assert ctx["committee_relevance"] is True and ctx["committee_temporal_status"] == "current_assignment_only"
    assert ctx["flagged_for_contextual_review"] is False and ctx["flag_pending_temporal_verification"] is True and ctx["meets_flag_rule"] is True
    assert client.get("/trades", params={"flagged": True}).json()["total"] == 0


def test_duplicate_looking_rows_are_grouped_for_display_but_never_merged(session_factory, client):
    from poltracker.models import Trade

    ids = seed(session_factory)
    with session_factory() as s:
        base = s.get(Trade, ids["big"])
        s.add(Trade(source="t", fingerprint="big-spouse", politician_id=base.politician_id, security_id=base.security_id, politician_name=base.politician_name, chamber="house",
                    ticker=base.ticker, asset_name="SP " + (base.asset_name or "x"), transaction_type=base.transaction_type, transaction_date=base.transaction_date,
                    disclosure_date=base.disclosure_date, amount_min=base.amount_min, amount_max=base.amount_max))
        s.commit()
    rows = client.get("/trades", params={"politician_id": ids["pol"], "limit": 50}).json()["items"]
    twins = [r for r in rows if r["transaction_date"] == "2026-02-20"]
    assert len(twins) == 2 and twins[0]["group_key"] == twins[1]["group_key"] and {r["group_size"] for r in twins} == {2}  # both rows kept
    assert {r["group_size"] for r in rows if r["transaction_date"] != "2026-02-20"} == {1}
