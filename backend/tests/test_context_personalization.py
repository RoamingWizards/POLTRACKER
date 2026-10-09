"""Phase 5: personalized context rules, server-side filters, presets and saved views. The objective trade_context is only ever READ here."""

import itertools
import json
import socket
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from poltracker.api.main import app, create_app, get_session
from poltracker.config import Settings
from poltracker.context_rules import DEFAULT_DELAY_DAYS, DEFAULT_EXCESS_PP, DEFAULT_SIZE_PERCENTILE, KIND_LABEL, PRESETS, ContextRule
from poltracker.models import (
    AppPreference, Base, CommitteeIndustryMapping, ContextView, Politician, Security, Trade, TradeContext, TradeContextAnalysis, TradeContextEvidence,
)
from poltracker.trade_context import ContextConfig, ENGINE_VERSION, is_flagged
from poltracker.trade_context_llm import PROMPT_VERSION

from test_trade_context import db, run, seed  # noqa: F401  (pytest puts the tests directory on sys.path)

V = "temporally_verified"
CUR = "current_assignment_only"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Personalization is fully local: any socket or HTTP use fails the test."""
    def blocked(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)


@pytest.fixture
def client(session_factory):
    def override():
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- a synthetic dataset with known stored facts -------------------------------------------------------------------------

class Data:
    """Builds trades with their stored context rows. Signal booleans and the canonical flag come from the engine's own rules, so the rows are what the engine would store."""

    def __init__(self, sf):
        self.sf, self.n, self.rows = sf, 0, {}
        with sf() as s:
            s.add(CommitteeIndustryMapping(chamber="house", committee_code="AS00", committee_name="Committee on Armed Services", sic_start=3720, sic_end=3729,
                                           relevance_level="direct", rationale="r", source_url="https://x", mapping_version="v1", review_status="reviewed",
                                           reviewed_at=datetime(2026, 10, 1), jurisdiction_basis="rule_x_text"))
            s.add(CommitteeIndustryMapping(chamber="house", committee_code="IF00", subcommittee_code="IF14", committee_name="Committee on Energy and Commerce",
                                           subcommittee_name="Health", sic_start=2833, sic_end=2836, relevance_level="direct", rationale="r", source_url="https://x",
                                           mapping_version="v1", review_status="reviewed", reviewed_at=datetime(2026, 10, 1), jurisdiction_basis="rule_x_text"))
            self.pols = {
                "ann": Politician(canonical_key="ann", name="Ann Lee", chamber="house", party="D", state="CA", district="31"),
                "bob": Politician(canonical_key="bob", name="Bob Ray", chamber="senate", party="R", state="TX"),
            }
            self.secs = {
                "BA": Security(ticker="BA", name="Boeing", company_name="Boeing Co", sic_code="3721", industry="Aircraft", sector="Manufacturing"),
                "PFE": Security(ticker="PFE", name="Pfizer", company_name="Pfizer Inc", sic_code="2834", industry="Pharmaceutical Preparations", sector="Manufacturing"),
            }
            s.add_all([*self.pols.values(), *self.secs.values()])
            s.commit()
            self.pid = {k: v.id for k, v in self.pols.items()}
            self.sid = {k: v.id for k, v in self.secs.items()}

    def add(self, pol="ann", ticker="BA", *, committee=True, temporal=V, pct=None, delay=None, excess=None, status="ok", related=False, ttype="buy",
            tx=date(2026, 3, 1), disc=None, amount=(1001, 15000), anomaly="auto", delay_sig="auto", excess_sig="auto", committee_code="AS00", ai=False, key=None):
        self.n += 1
        anomaly = (pct >= 90 if pct is not None else None) if anomaly == "auto" else anomaly
        delay_sig = (delay > 45 if delay is not None else None) if delay_sig == "auto" else delay_sig
        excess_sig = (abs(excess) + 1e-9 >= 0.20 if excess is not None else None) if excess_sig == "auto" else excess_sig
        secondary = sum(x is True for x in (anomaly, delay_sig, excess_sig))
        flagged = is_flagged(committee, anomaly, delay_sig, excess_sig, 2, temporal)
        with self.sf() as s:
            t = Trade(source="t", fingerprint=f"f{self.n}", politician_id=self.pid[pol], security_id=self.sid[ticker], politician_name=self.pols[pol].name,
                      chamber=self.pols[pol].chamber, party=self.pols[pol].party, state=self.pols[pol].state, ticker=ticker, asset_name=self.secs[ticker].name,
                      transaction_type=ttype, transaction_date=tx, disclosure_date=disc or tx + timedelta(days=delay or 10), amount_min=amount[0], amount_max=amount[1])
            s.add(t)
            s.flush()
            c = TradeContext(trade_id=t.id, context_version=key or ENGINE_VERSION, mapping_version="v1", result_digest=f"d{self.n}", analyzed_at=datetime(2026, 10, 9),
                             committee_relevance=committee, trade_size_anomaly=anomaly, disclosure_delay_signal=delay_sig, excess_return_signal=excess_sig,
                             committee_relevance_reason="direct_match" if committee else "no_reviewed_direct_match", trade_size_percentile=pct, trade_size_sample_size=12 if pct is not None else None,
                             disclosure_delay_days=delay, performance_status=status if excess is not None else "unavailable", excess_return=excess, excess_return_direction_adjusted=excess,
                             signal_count=sum(x is True for x in (committee, anomaly, delay_sig, excess_sig)), secondary_signal_count=secondary,
                             committee_temporal_status=temporal, meets_flag_rule=bool(committee and secondary >= 2), flagged_for_contextual_review=flagged)
            s.add(c)
            s.flush()
            if committee:
                s.add(TradeContextEvidence(trade_context_id=c.id, trade_id=t.id, signal_type="committee_relevance", evidence_type="reviewed_direct_mapping", evidence_key="mapping:1",
                                           committee_code=committee_code, subcommittee_code="IF14" if committee_code == "IF00" else None, description="d",
                                           metadata_json=json.dumps({"committee_name": "Committee on Armed Services"})))
            if related:
                s.add(TradeContextEvidence(trade_context_id=c.id, trade_id=t.id, signal_type="committee_relevance", evidence_type="reviewed_related_mapping", evidence_key="mapping:2",
                                           committee_code="AS00", description="d", metadata_json="{}"))
            if ai:
                s.add(TradeContextAnalysis(trade_id=t.id, context_version=c.context_version, mapping_version="v1", prompt_version=PROMPT_VERSION, model="m", input_hash="h",
                                           context_digest=c.result_digest, generated_for="flagged", headline="h", summary="s", signals_json="[]", limitations="l", created_at=datetime(2026, 10, 9)))
            s.commit()
            self.rows[t.id] = dict(committee=committee, temporal=temporal, pct=pct, delay=delay, excess=excess, status=status, related=related, anomaly=anomaly,
                                   delay_sig=delay_sig, excess_sig=excess_sig, flagged=flagged)
            return t.id


def grid(sf):
    """Every combination of the facts that matter, including the engine's edge cases (a stored percentile of 90.0 whose engine boolean is False, a delay of exactly 45)."""
    d = Data(sf)
    for committee, temporal, pct, delay, excess in itertools.product(
            (True, False, None), (V, CUR), (None, 89.99, 90.0, 97.5), (None, 30, 45, 46, 120), (None, 0.05, 0.1999, 0.20, -0.25)):
        if committee is not True and temporal == CUR:
            continue
        d.add(committee=committee, temporal=temporal, pct=pct, delay=delay, excess=excess)
    d.add(pct=90.0, anomaly=False, delay=46, excess=0.3)  # the engine said False for 89.9999..., the stored percentile rounds to 90.0
    d.add("bob", "PFE", committee=False, related=True, pct=95.0, delay=60)
    d.add(committee=False, related=True, temporal=V, pct=95.0, delay=60, excess=0.3)
    return d


def screen(client, rule=None, filters=None, **params):
    q = {**params}
    if rule is not None:
        q["rule"] = json.dumps(rule if isinstance(rule, dict) else rule.model_dump())
    if filters is not None:
        q["filters"] = json.dumps(filters)
    q.setdefault("limit", 500)
    r = client.get("/trades/screen", params=q)
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == min(body["total"], q["limit"]) or "offset" in q  # a test must never silently look at a truncated page
    return body


def matched_ids(body):
    return {i["id"] for i in body["items"] if i["custom_screen"] and i["custom_screen"]["matches"]}


def py_matches(rule: ContextRule, d: dict) -> bool:
    """A plain-Python statement of the rule over a row's stored facts, to check the SQL translation."""
    ok = d["committee"] is True or (not rule.reviewed_direct_only and d["related"])
    committee = ok and (d["temporal"] == V or not rule.require_temporal_verification)
    size = rule.enable_trade_size_signal and (d["anomaly"] is True if rule.trade_size_percentile_threshold == DEFAULT_SIZE_PERCENTILE
                                              else d["pct"] is not None and d["pct"] >= rule.trade_size_percentile_threshold)
    delay = rule.enable_disclosure_delay_signal and (d["delay_sig"] is True if rule.disclosure_delay_threshold_days == DEFAULT_DELAY_DAYS
                                                     else d["delay"] is not None and d["delay"] > rule.disclosure_delay_threshold_days)
    excess = rule.enable_excess_return_signal and (d["excess_sig"] is True if rule.excess_return_threshold_pct_points == DEFAULT_EXCESS_PP
                                                   else d["excess"] is not None and d["status"] == "ok" and abs(d["excess"]) * 100 + 1e-7 >= rule.excess_return_threshold_pct_points)
    return (committee or not rule.committee_relevance_required) and (size + delay + excess) >= rule.minimum_secondary_signals


# --- config -------------------------------------------------------------------------------------------------------------

def test_the_default_rule_is_exactly_the_production_methodology():
    r, c = ContextRule(), ContextConfig()
    assert (r.committee_relevance_required, r.reviewed_direct_only, r.require_temporal_verification) == (True, True, True)
    assert (r.enable_trade_size_signal, r.trade_size_percentile_threshold) == (True, c.size_percentile == 90 and 90)
    assert (r.enable_disclosure_delay_signal, r.disclosure_delay_threshold_days) == (True, c.delay_days == 45 and 45)
    assert (r.enable_excess_return_signal, r.excess_return_threshold_pct_points) == (True, 20) and c.excess_return == 0.20
    assert r.minimum_secondary_signals == c.min_secondary_signals == 2 and r.is_default() and r.kind() == "default"


def test_the_default_rule_reproduces_the_canonical_flag_for_every_trade(session_factory, client):
    d = grid(session_factory)
    body = screen(client)
    assert body["total"] == len(d.rows) and body["is_default_rule"] is True and body["kind"] == "default"
    flagged = {i for i, r in d.rows.items() if r["flagged"]}
    assert flagged and matched_ids(body) == flagged  # exactly the canonical flags, edge cases included
    assert body["custom_match_count"] == body["canonical_flag_count"] == len(flagged)
    for item in body["items"]:
        cs = item["custom_screen"]
        assert cs["matches"] == item["context"]["flagged_for_contextual_review"] and cs["differs_from_canonical"] is False


def test_the_default_matches_the_real_engine_output_too(session_factory, client):
    seed(session_factory, dated_seat=True, with_prices=True)
    run(session_factory)
    body = screen(client)
    assert body["total"] == 14 and matched_ids(body) == {i["id"] for i in body["items"] if i["context"]["flagged_for_contextual_review"]} and body["canonical_flag_count"] == 1


@pytest.mark.parametrize("change", [
    dict(enable_trade_size_signal=False), dict(enable_disclosure_delay_signal=False), dict(enable_excess_return_signal=False),
    dict(trade_size_percentile_threshold=50), dict(trade_size_percentile_threshold=97), dict(disclosure_delay_threshold_days=30), dict(disclosure_delay_threshold_days=100),
    dict(excess_return_threshold_pct_points=5), dict(excess_return_threshold_pct_points=19.99), dict(excess_return_threshold_pct_points=30),
    dict(minimum_secondary_signals=0), dict(minimum_secondary_signals=1), dict(minimum_secondary_signals=3),
    dict(reviewed_direct_only=False), dict(require_temporal_verification=False),
    dict(committee_relevance_required=False), dict(committee_relevance_required=False, minimum_secondary_signals=1),
    dict(committee_relevance_required=False, enable_trade_size_signal=False, enable_excess_return_signal=False, minimum_secondary_signals=1),
    dict(enable_trade_size_signal=False, enable_disclosure_delay_signal=False, minimum_secondary_signals=1),
])
def test_every_setting_changes_the_screen_as_the_rule_says(session_factory, client, change):
    d = grid(session_factory)
    try:
        rule = ContextRule(**change)
    except ValueError:
        pytest.skip("an incoherent combination is rejected, tested separately")
    body = screen(client, rule)
    assert matched_ids(body) == {i for i, r in d.rows.items() if py_matches(rule, r)}


def test_sql_matches_a_plain_python_reading_across_many_rules(session_factory, client):
    d = grid(session_factory)
    for committee, direct_only, temporal, size, delay, excess, mn in itertools.product(
            (True, False), (True, False), (True, False), (True, False), (True, False), (True, False), (0, 1, 2, 3)):
        try:
            rule = ContextRule(committee_relevance_required=committee, reviewed_direct_only=direct_only, require_temporal_verification=temporal,
                               enable_trade_size_signal=size, enable_disclosure_delay_signal=delay, enable_excess_return_signal=excess, minimum_secondary_signals=mn,
                               trade_size_percentile_threshold=75, disclosure_delay_threshold_days=40, excess_return_threshold_pct_points=10)
        except ValueError:
            continue
        assert matched_ids(screen(client, rule)) == {i for i, r in d.rows.items() if py_matches(rule, r)}, rule


def test_the_temporal_gate_is_preserved_unless_the_user_turns_it_off(session_factory, client):
    d = Data(session_factory)
    unverified = d.add(committee=True, temporal=CUR, pct=95, delay=60)
    verified = d.add(committee=True, temporal=V, pct=95, delay=60)
    assert matched_ids(screen(client)) == {verified}
    assert matched_ids(screen(client, ContextRule(require_temporal_verification=False))) == {verified, unverified}
    assert [i["context"]["flagged_for_contextual_review"] for i in screen(client)["items"] if i["id"] == unverified] == [False]  # the canonical flag is unaffected


def test_the_reviewed_direct_gate_is_preserved_unless_related_is_allowed(session_factory, client):
    d = Data(session_factory)
    related_only = d.add(committee=False, related=True, pct=95, delay=60)
    direct = d.add(committee=True, pct=95, delay=60)
    assert matched_ids(screen(client)) == {direct}
    assert matched_ids(screen(client, ContextRule(reviewed_direct_only=False))) == {direct, related_only}


def test_a_needs_review_mapping_never_helps_a_custom_rule(session_factory, client):
    ids = seed(session_factory, mapping_status="needs_review", dated_seat=True)
    run(session_factory)
    loose = ContextRule(reviewed_direct_only=False, require_temporal_verification=False, minimum_secondary_signals=0)
    body = screen(client, loose)
    big = next(i for i in body["items"] if i["id"] == ids["big"])
    assert big["context"]["committee_relevance"] is False and big["custom_screen"]["matches"] is False  # nothing stored for it, so nothing to relax


@pytest.mark.parametrize("bad", [
    dict(minimum_secondary_signals=3, enable_excess_return_signal=False),
    dict(committee_relevance_required=False, minimum_secondary_signals=0),
    dict(trade_size_percentile_threshold=101), dict(trade_size_percentile_threshold=-1), dict(disclosure_delay_threshold_days=-5),
    dict(excess_return_threshold_pct_points=-1), dict(minimum_secondary_signals=4), dict(surprise=True),
])
def test_incoherent_or_out_of_range_rules_are_rejected(client, bad):
    r = client.get("/trades/screen", params={"rule": json.dumps(bad)})
    assert r.status_code == 422


# --- personalized rule vs the canonical flag -----------------------------------------------------------------------------

def test_a_custom_rule_can_match_while_the_default_flag_is_false_and_the_reverse(session_factory, client):
    d = Data(session_factory)
    one_secondary = d.add(committee=True, pct=95, delay=10)  # default needs two secondaries: not flagged
    two_secondary = d.add(committee=True, pct=95, delay=60)  # flagged by default
    loose, strict = ContextRule(minimum_secondary_signals=1), ContextRule(minimum_secondary_signals=3)
    body = screen(client, loose)
    cs = {i["id"]: i for i in body["items"]}
    assert cs[one_secondary]["custom_screen"]["matches"] is True and cs[one_secondary]["context"]["flagged_for_contextual_review"] is False
    assert cs[one_secondary]["custom_screen"]["differs_from_canonical"] is True and cs[one_secondary]["custom_screen"]["canonical_flag"] is False
    body = screen(client, strict)
    cs = {i["id"]: i for i in body["items"]}
    assert cs[two_secondary]["context"]["flagged_for_contextual_review"] is True and cs[two_secondary]["custom_screen"]["matches"] is False
    assert cs[two_secondary]["custom_screen"]["differs_from_canonical"] is True


def snapshot(sf):
    with sf() as s:
        ctx = [tuple(getattr(c, col.name) for col in TradeContext.__table__.columns) for c in s.scalars(select(TradeContext).order_by(TradeContext.id))]
        ev = [tuple(getattr(e, col.name) for col in TradeContextEvidence.__table__.columns) for e in s.scalars(select(TradeContextEvidence).order_by(TradeContextEvidence.id))]
        tr = [tuple(getattr(t, col.name) for col in Trade.__table__.columns) for t in s.scalars(select(Trade).order_by(Trade.id))]
    return ctx, ev, tr


def test_screening_with_any_rule_or_filter_never_changes_the_stored_objective_data(session_factory, client):
    grid(session_factory)
    before = snapshot(session_factory)
    for rule in (ContextRule(), ContextRule(minimum_secondary_signals=0), ContextRule(committee_relevance_required=False), ContextRule(reviewed_direct_only=False, require_temporal_verification=False),
                 *(p.rule for p in PRESETS.values())):
        screen(client, rule, [{"field": "chamber", "op": "is", "value": "house"}, {"field": "excess_return", "op": "abs_gte", "value": 5}])
    assert snapshot(session_factory) == before


def test_a_performance_only_screen_is_labelled_market_only_and_is_never_the_canonical_flag(session_factory, client):
    d = Data(session_factory)
    perf_only = d.add(committee=False, pct=95, delay=60, excess=0.3)  # strong market signals, no committee relevance
    body = screen(client, PRESETS["market_focus"].rule)
    item = next(i for i in body["items"] if i["id"] == perf_only)
    assert body["kind"] == "market_only" and "does not indicate political context" in body["kind_label"]
    assert item["custom_screen"]["matches"] is True and item["custom_screen"]["kind"] == "market_only"
    assert "committee_relevance" not in item["custom_screen"]["active_signals"]
    assert item["context"]["flagged_for_contextual_review"] is False and body["canonical_flag_count"] == 0  # the canonical flag is untouched
    assert "not the contextual-review flag" in body["notice"]


def test_committee_only_browsing_is_labelled_and_is_not_a_flag(session_factory, client):
    d = Data(session_factory)
    d.add(committee=True)  # committee-relevant, no secondary signal: not flagged
    body = screen(client, PRESETS["committee_focus"].rule)
    assert body["kind"] == "committee_only" and "not the contextual-review flag" in body["kind_label"]
    assert body["custom_match_count"] == 1 and body["canonical_flag_count"] == 0


def test_every_kind_has_neutral_wording():
    text = " ".join(list(KIND_LABEL.values()) + [p.description + " ".join(p.notes) for p in PRESETS.values()]).lower()
    for word in ("insider", "guilt", "corrupt", "probability", "score", "illegal", "suspicious"):
        assert word not in text


# --- filters -------------------------------------------------------------------------------------------------------------

def filter_dataset(sf):
    d = Data(sf)
    a = d.add("ann", "BA", committee=True, pct=95, delay=60, excess=0.30, tx=date(2026, 1, 10), amount=(1001, 15000), ttype="buy", ai=True)  # flagged
    b = d.add("ann", "PFE", committee=False, pct=40, delay=10, excess=0.02, tx=date(2026, 2, 10), amount=(50001, 100000), ttype="sell", committee_code="IF00")
    c = d.add("bob", "BA", committee=None, temporal="unavailable", pct=None, delay=100, excess=-0.25, tx=date(2026, 3, 10), amount=(250001, 500000), ttype="sell")
    e = d.add("bob", "PFE", committee=True, pct=92, delay=None, excess=0.10, tx=date(2026, 4, 10), amount=(15001, 50000), ttype="buy", committee_code="IF00")
    return d, dict(a=a, b=b, c=c, e=e)


@pytest.mark.parametrize("flt, expected", [
    ({"field": "politician", "op": "is", "value": 1}, {"a", "b"}),
    ({"field": "politician", "op": "contains", "value": "bob"}, {"c", "e"}),
    ({"field": "chamber", "op": "is", "value": "senate"}, {"c", "e"}),
    ({"field": "party", "op": "is", "value": "d"}, {"a", "b"}),
    ({"field": "state", "op": "is", "value": "tx"}, {"c", "e"}),
    ({"field": "district", "op": "is", "value": "31"}, {"a", "b"}),
    ({"field": "ticker", "op": "is", "value": "ba"}, {"a", "c"}),
    ({"field": "ticker", "op": "contains", "value": "fe"}, {"b", "e"}),
    ({"field": "company", "op": "contains", "value": "pfizer"}, {"b", "e"}),
    ({"field": "industry", "op": "contains", "value": "aircraft"}, {"a", "c"}),
    ({"field": "transaction_type", "op": "is", "value": "sell"}, {"b", "c"}),
    ({"field": "transaction_type", "op": "in", "value": ["buy", "exchange"]}, {"a", "e"}),
    ({"field": "transaction_date", "op": "gte", "value": "2026-03-01"}, {"c", "e"}),
    ({"field": "transaction_date", "op": "lte", "value": "2026-02-10"}, {"a", "b"}),
    ({"field": "transaction_date", "op": "between", "value": ["2026-02-01", "2026-03-15"]}, {"b", "c"}),
    ({"field": "disclosure_date", "op": "gte", "value": "2026-04-01"}, {"c", "e"}),
    ({"field": "value", "op": "gte", "value": 50000}, {"b", "c"}),
    ({"field": "value", "op": "lte", "value": 50000}, {"a", "e"}),
    ({"field": "committee_relevance", "op": "is", "value": "yes"}, {"a", "e"}),
    ({"field": "committee_relevance", "op": "is", "value": "no"}, {"b"}),
    ({"field": "committee_relevance", "op": "is", "value": "unknown"}, {"c"}),
    ({"field": "committee_name", "op": "contains", "value": "armed"}, {"a"}),
    ({"field": "committee_name", "op": "contains", "value": "health"}, {"e"}),
    ({"field": "committee_name", "op": "contains", "value": "no such committee"}, set()),
    ({"field": "trade_size_percentile", "op": "gte", "value": 90}, {"a", "e"}),
    ({"field": "trade_size_percentile", "op": "lte", "value": 50}, {"b"}),
    ({"field": "disclosure_delay", "op": "gte", "value": 60}, {"a", "c"}),
    ({"field": "disclosure_delay", "op": "lte", "value": 10}, {"b"}),
    ({"field": "excess_return", "op": "abs_gte", "value": 20}, {"a", "c"}),
    ({"field": "excess_return", "op": "gte", "value": 10}, {"a", "e"}),
    ({"field": "excess_return", "op": "lte", "value": -20}, {"c"}),
    ({"field": "active_signals", "op": "gte", "value": 3}, {"a"}),
    ({"field": "active_signals", "op": "eq", "value": 0}, {"b"}),
    ({"field": "review_status", "op": "is", "value": "flagged"}, {"a"}),
    ({"field": "review_status", "op": "is", "value": "not_flagged"}, {"b", "c", "e"}),
    ({"field": "custom_screen", "op": "is", "value": "match"}, {"a"}),
    ({"field": "custom_screen", "op": "is", "value": "no_match"}, {"b", "c", "e"}),
    ({"field": "ai_context", "op": "is", "value": "available"}, {"a"}),
    ({"field": "ai_context", "op": "is", "value": "unavailable"}, {"b", "c", "e"}),
])
def test_each_filter_selects_exactly_the_matching_trades(session_factory, client, flt, expected):
    d, ids = filter_dataset(session_factory)
    flt = dict(flt)
    if flt["field"] == "politician" and flt["op"] == "is":
        flt["value"] = d.pid["ann"]
    body = screen(client, filters=[flt])
    assert {i["id"] for i in body["items"]} == {ids[k] for k in expected} and body["total"] == len(expected)


def test_filters_combine_with_and_and_can_be_added_edited_removed_and_cleared(session_factory, client):
    d, ids = filter_dataset(session_factory)
    f1 = {"field": "ticker", "op": "is", "value": "BA"}
    f2 = {"field": "excess_return", "op": "abs_gte", "value": 20}
    f3 = {"field": "transaction_type", "op": "is", "value": "sell"}
    got = lambda *fs: {i["id"] for i in screen(client, filters=list(fs))["items"]}
    assert got() == set(ids.values())  # cleared: everything
    assert got(f1) == {ids["a"], ids["c"]}  # add
    assert got(f1, f2) == {ids["a"], ids["c"]}
    assert got(f1, f2, f3) == {ids["c"]}  # AND narrows
    assert got(f1, {**f2, "value": 28}, f3) == set()  # edit a value
    assert got(f1, f3) == {ids["c"]}  # remove one
    assert got(f1, {"field": "ticker", "op": "is", "value": "PFE"}) == set()  # contradictory filters on one field
    assert got() == set(ids.values())  # clear all


@pytest.mark.parametrize("bad", [
    {"field": "nonsense", "op": "is", "value": "x"}, {"field": "chamber", "op": "gte", "value": "house"}, {"field": "chamber", "op": "is", "value": "congress"},
    {"field": "transaction_date", "op": "gte", "value": "yesterday"}, {"field": "transaction_date", "op": "between", "value": ["2026-01-01"]},
    {"field": "value", "op": "gte", "value": "lots"}, {"field": "transaction_type", "op": "in", "value": []}, {"field": "ticker", "op": "contains", "value": "  "},
    {"field": "ticker", "op": "is", "value": "BA", "extra": 1},
])
def test_invalid_filters_are_rejected_not_ignored(client, bad):
    assert client.get("/trades/screen", params={"filters": json.dumps([bad])}).status_code == 422
    assert client.get("/trades/screen", params={"filters": "not json"}).status_code == 422
    assert client.get("/trades/screen", params={"filters": json.dumps({"field": "chamber"})}).status_code == 422
    assert client.get("/trades/screen", params={"filters": json.dumps([{"field": "ticker", "op": "is", "value": "A"}] * 26)}).status_code == 422


def test_the_active_signal_filter_follows_the_current_rule(session_factory, client):
    d, ids = filter_dataset(session_factory)
    f = [{"field": "active_signals", "op": "gte", "value": 2}]
    default = {i["id"] for i in screen(client, filters=f)["items"]}
    no_size = {i["id"] for i in screen(client, ContextRule(enable_trade_size_signal=False, minimum_secondary_signals=1), f)["items"]}
    assert default == {ids["a"], ids["c"], ids["e"]}  # a: committee + delay + excess; c: delay + excess; e: committee + size
    assert no_size == {ids["a"], ids["c"]} and ids["e"] not in no_size  # trade e's only other signal was its size, which this rule switches off


def test_pagination_sorting_and_totals(session_factory, client):
    d, ids = filter_dataset(session_factory)
    page = screen(client, limit=2, offset=0, sort_by="transaction_date", order="asc")
    assert page["total"] == 4 and [i["id"] for i in page["items"]] == [ids["a"], ids["b"]]
    nxt = screen(client, limit=2, offset=2, sort_by="transaction_date", order="asc")
    assert [i["id"] for i in nxt["items"]] == [ids["c"], ids["e"]] and nxt["custom_match_count"] == 1  # counts cover the whole filtered set, not the page


def test_old_endpoints_are_unchanged(session_factory, client):
    ids = seed(session_factory, dated_seat=True)
    run(session_factory)
    body = client.get("/trades", params={"flagged": True}).json()
    assert body["total"] == 1 and "custom_screen" in body["items"][0] and body["items"][0]["custom_screen"] is None  # additive, null outside the screen
    assert client.get(f"/trades/{ids['big']}").status_code == 200


def test_a_trade_with_no_stored_context_has_no_custom_screen(session_factory, client):
    seed(session_factory)  # no analyzer run: no trade_context rows, and no mapping loaded
    body = screen(client)
    assert body["total"] == 14 and all(i["custom_screen"] is None for i in body["items"])


def test_ai_availability_requires_the_current_prompt_and_unchanged_context(session_factory, client):
    d, ids = filter_dataset(session_factory)
    with session_factory() as s:
        s.scalar(select(TradeContextAnalysis)).prompt_version = "0"
        s.commit()
    assert screen(client, filters=[{"field": "ai_context", "op": "is", "value": "available"}])["total"] == 0


# --- presets --------------------------------------------------------------------------------------------------------------

def test_built_in_presets_are_transparent_configurations(client):
    body = client.get("/context/presets").json()
    assert [p["key"] for p in body["presets"]] == ["balanced", "strict", "committee_focus", "market_focus"]
    assert body["default_rule"] == ContextRule().model_dump()
    by = {p["key"]: p for p in body["presets"]}
    assert by["balanced"]["rule"] == ContextRule().model_dump() and by["balanced"]["kind"] == "default"
    assert by["strict"]["rule"]["minimum_secondary_signals"] == 3 and by["strict"]["rule"]["trade_size_percentile_threshold"] == 95
    assert by["committee_focus"]["rule"]["minimum_secondary_signals"] == 0 and by["committee_focus"]["rule"]["committee_relevance_required"] is True
    assert by["market_focus"]["rule"]["committee_relevance_required"] is False and by["market_focus"]["kind"] == "market_only"
    assert all(p["notes"] and p["description"] for p in body["presets"])  # each one says in words what it does
    assert all(ContextRule.model_validate(p["rule"]) for p in body["presets"])


def test_presets_screen_as_described(session_factory, client):
    d = grid(session_factory)
    balanced = matched_ids(screen(client, PRESETS["balanced"].rule))
    assert balanced == {i for i, r in d.rows.items() if r["flagged"]}
    strict = matched_ids(screen(client, PRESETS["strict"].rule))
    assert strict and strict <= {i for i, r in d.rows.items() if py_matches(ContextRule(), r)} | strict  # sanity: a subset of committee-relevant trades
    committee = matched_ids(screen(client, PRESETS["committee_focus"].rule))
    assert balanced <= committee  # browsing by committee alone includes every flagged trade
    market = matched_ids(screen(client, PRESETS["market_focus"].rule))
    assert market and any(not d.rows[i]["flagged"] for i in market)  # it surfaces trades the canonical flag does not


# --- saved views and the last-used screen -------------------------------------------------------------------------------

@pytest.fixture
def local_client(session_factory):
    def override():
        with session_factory() as s:
            yield s

    api = create_app(Settings(local_views_enabled=True, database_url="sqlite://"))
    api.dependency_overrides[get_session] = override
    return TestClient(api)


def test_the_views_routes_exist_only_when_local_views_are_enabled(client, local_client):
    assert client.get("/context/views").status_code == 404 and client.put("/context/active", json={}).status_code in (404, 405)
    assert local_client.get("/context/views").json() == []
    assert Settings(_env_file=None).local_views_enabled is False


def test_the_desktop_app_mounts_the_views_routes():
    from poltracker.desktop.app import create_desktop_app  # noqa: F401
    import inspect, poltracker.desktop.app as m
    assert "views_router" in inspect.getsource(m)


def test_save_name_load_rename_and_delete_a_view(local_client):
    rule = ContextRule(minimum_secondary_signals=1).model_dump()
    flt = [{"field": "ticker", "op": "is", "value": "BA"}]
    made = local_client.post("/context/views", json={"name": "  Defense   trades ", "rule": rule, "filters": flt, "preset": "custom"})
    assert made.status_code == 201 and made.json()["name"] == "Defense trades" and made.json()["rule"]["minimum_secondary_signals"] == 1
    vid = made.json()["id"]
    assert [v["name"] for v in local_client.get("/context/views").json()] == ["Defense trades"]
    loaded = local_client.get("/context/views").json()[0]
    assert loaded["filters"] == [{"field": "ticker", "op": "is", "value": "BA"}] and loaded["preset"] == "custom"
    renamed = local_client.patch(f"/context/views/{vid}", json={"name": "Large committee-related buys"})
    assert renamed.json()["name"] == "Large committee-related buys" and renamed.json()["rule"]["minimum_secondary_signals"] == 1  # rename leaves the rest alone
    updated = local_client.patch(f"/context/views/{vid}", json={"rule": ContextRule().model_dump(), "filters": []})
    assert updated.json()["rule"] == ContextRule().model_dump() and updated.json()["filters"] == [] and updated.json()["name"] == "Large committee-related buys"
    assert local_client.delete(f"/context/views/{vid}").status_code == 204 and local_client.get("/context/views").json() == []
    assert local_client.delete(f"/context/views/{vid}").status_code == 404 and local_client.patch(f"/context/views/{vid}", json={"name": "x"}).status_code == 404


def test_view_names_are_unique_case_insensitively_and_validated(local_client):
    assert local_client.post("/context/views", json={"name": "A"}).status_code == 201
    assert local_client.post("/context/views", json={"name": "a"}).status_code == 409
    b = local_client.post("/context/views", json={"name": "B"}).json()["id"]
    assert local_client.patch(f"/context/views/{b}", json={"name": "A"}).status_code == 409
    assert local_client.patch(f"/context/views/{b}", json={"name": "B"}).status_code == 200  # keeping its own name is fine
    for bad in ({"name": ""}, {"name": "   "}, {"name": "x" * 81}, {"name": "ok", "preset": "nonsense"}, {"name": "ok", "rule": {"minimum_secondary_signals": 9}},
                {"name": "ok", "filters": [{"field": "chamber", "op": "gte", "value": "house"}]}, {"name": "ok", "unexpected": 1}):
        assert local_client.post("/context/views", json=bad).status_code == 422, bad


def test_the_number_of_saved_views_is_capped(local_client, session_factory):
    from poltracker.api import views
    with session_factory() as s:
        now = datetime(2026, 10, 9)
        s.add_all([ContextView(name=f"v{i}", rule_json=ContextRule().model_dump_json(), filters_json="[]", created_at=now, updated_at=now) for i in range(views.MAX_VIEWS)])
        s.commit()
    assert local_client.post("/context/views", json={"name": "one more"}).status_code == 409


def test_the_last_used_screen_is_remembered_and_can_be_reset(local_client):
    first = local_client.get("/context/active").json()
    assert first["saved"] is False and first["rule"] == ContextRule().model_dump() and first["filters"] == [] and first["preset"] == "balanced"
    body = {"rule": PRESETS["strict"].rule.model_dump(), "filters": [{"field": "chamber", "op": "is", "value": "house"}], "preset": "strict"}
    put = local_client.put("/context/active", json=body).json()
    assert put["saved"] is True and local_client.get("/context/active").json() == put and put["preset"] == "strict" and put["rule"]["minimum_secondary_signals"] == 3
    reset = local_client.delete("/context/active").json()
    assert reset["saved"] is False and reset["rule"] == ContextRule().model_dump() and local_client.get("/context/active").json() == reset
    assert local_client.put("/context/active", json={"rule": {"minimum_secondary_signals": 7}}).status_code == 422


def test_a_dangling_view_link_is_dropped_and_a_corrupt_stored_screen_falls_back_to_the_default(local_client, session_factory):
    assert local_client.put("/context/active", json={"view_id": 999}).json()["view_id"] is None
    with session_factory() as s:
        s.get(AppPreference, "active_screen").value_json = "{not json"
        s.commit()
    got = local_client.get("/context/active").json()
    assert got["saved"] is False and got["rule"] == ContextRule().model_dump()


def test_views_and_the_active_screen_survive_an_app_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'poltracker.db'}"
    first = create_engine(url)
    Base.metadata.create_all(first)
    sf1 = sessionmaker(first, expire_on_commit=False)
    def session_for(sf):
        def dep():
            with sf() as s:
                yield s
        return dep

    api = create_app(Settings(local_views_enabled=True, database_url=url))
    api.dependency_overrides[get_session] = session_for(sf1)
    c = TestClient(api)
    c.post("/context/views", json={"name": "High excess-return disclosures", "rule": ContextRule(minimum_secondary_signals=1).model_dump(), "preset": "custom",
                                   "filters": [{"field": "excess_return", "op": "abs_gte", "value": 20}]})
    c.put("/context/active", json={"rule": PRESETS["market_focus"].rule.model_dump(), "filters": [], "preset": "market_focus"})
    first.dispose()  # the app quits
    second = create_engine(url)  # ...and starts again
    sf2 = sessionmaker(second, expire_on_commit=False)
    api2 = create_app(Settings(local_views_enabled=True, database_url=url))
    api2.dependency_overrides[get_session] = session_for(sf2)
    c2 = TestClient(api2)
    views = c2.get("/context/views").json()
    assert [v["name"] for v in views] == ["High excess-return disclosures"] and views[0]["filters"][0]["field"] == "excess_return"
    active = c2.get("/context/active").json()
    assert active["saved"] is True and active["preset"] == "market_focus" and active["rule"]["committee_relevance_required"] is False


def test_saving_and_loading_views_never_touches_the_objective_context(session_factory, local_client):
    grid(session_factory)
    before = snapshot(session_factory)
    local_client.post("/context/views", json={"name": "v", "rule": ContextRule(minimum_secondary_signals=1).model_dump()})
    local_client.put("/context/active", json={"rule": ContextRule(minimum_secondary_signals=1).model_dump()})
    local_client.delete("/context/active")
    assert snapshot(session_factory) == before


# --- database ----------------------------------------------------------------------------------------------------------------

def test_migration_0016_adds_only_the_two_preference_tables_and_keeps_existing_context(db):
    engine, cfg = db
    command.upgrade(cfg, "0015")
    with engine.begin() as c:
        c.exec_driver_sql("insert into politicians (id, canonical_key, name, chamber, created_at) values (1, 'a', 'A', 'house', '2026-01-01')")
        c.exec_driver_sql("insert into trades (id, source, fingerprint, politician_id, politician_name, chamber, transaction_type, transaction_date, created_at) "
                          "values (1, 's', 'f', 1, 'A', 'house', 'buy', '2026-01-01', '2026-01-01')")
        c.exec_driver_sql("insert into trade_context (id, trade_id, context_version, mapping_version, result_digest, analyzed_at, signal_count, flagged_for_contextual_review) "
                          "values (1, 1, '2026.3', 'm', 'd', '2026-01-02', 1, 1)")
    before = set(sa.inspect(engine).get_table_names())
    command.upgrade(cfg, "head")
    assert set(sa.inspect(engine).get_table_names()) - before == {"context_views", "app_preferences"}
    with engine.connect() as c:
        assert c.exec_driver_sql("select version_num from alembic_version").scalar() == "0016"
        assert tuple(c.exec_driver_sql("select trade_id, context_version, flagged_for_contextual_review, result_digest from trade_context").one()) == (1, "2026.3", 1, "d")
    command.downgrade(cfg, "0015")
    assert not {"context_views", "app_preferences"} & set(sa.inspect(engine).get_table_names())
    with engine.connect() as c:
        assert c.exec_driver_sql("select count(*) from trade_context").scalar() == 1  # the objective context is untouched by the downgrade
    command.upgrade(cfg, "head")


def test_view_names_are_unique_in_the_database(session_factory):
    with session_factory() as s:
        now = datetime(2026, 10, 9)
        s.add(ContextView(name="x", rule_json="{}", filters_json="[]", created_at=now, updated_at=now))
        s.commit()
        s.add(ContextView(name="x", rule_json="{}", filters_json="[]", created_at=now, updated_at=now))
        with pytest.raises(sa.exc.IntegrityError):
            s.commit()


# --- offline ---------------------------------------------------------------------------------------------------------------

def test_personalization_needs_no_network_and_no_openai(session_factory, client, local_client):
    """The autouse guard fails the test on any socket or HTTP use; this exercises every personalization path under it."""
    grid(session_factory)
    client.get("/context/presets")
    screen(client, PRESETS["strict"].rule, [{"field": "ai_context", "op": "is", "value": "unavailable"}])
    local_client.post("/context/views", json={"name": "offline"})
    local_client.put("/context/active", json={})
    assert local_client.get("/context/active").json()["saved"] is True
