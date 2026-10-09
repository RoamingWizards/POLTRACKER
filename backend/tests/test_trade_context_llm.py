"""OpenAI-written trade-context explanations: validated, cached, optional, and never able to change a signal or the flag. No test makes a live request."""

import json
from datetime import date

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import poltracker.analyze_trade_context_llm as svc_mod
import poltracker.trade_context as tc
from poltracker.analyze_trade_context_llm import TradeContextExplanationService, main
from poltracker.api.main import app, get_session
from poltracker.config import Settings
from poltracker.models import CommitteeIndustryMapping, Trade, TradeContext, TradeContextAnalysis, TradeContextEvidence
from poltracker.trade_context_llm import (
    PROMPT_VERSION, SCHEMA, SYSTEM, Explanation, ExplanationError, ExplanationRejected, OpenAIExplainer, build_explainer, build_facts, input_hash,
    parse_explanation, validate_explanation,
)

from test_trade_context import ROOT, db, run, seed  # noqa: F401  (pytest puts the tests directory on sys.path)

MODEL = "test-model"
GOOD = {
    "headline": "Armed Services seat and a long disclosure delay on an aircraft-industry purchase",
    "summary": ("The member held a temporally verified Armed Services seat on the transaction date and bought a company in SIC 3721 (Aircraft). The disclosed range was "
                "$250,001 to $500,000, at the 100th percentile of 12 earlier trades, and the disclosure came 59 days after the transaction. POLTRACKER flagged the trade for "
                "contextual review; this does not establish wrongdoing."),
    "signals": [
        {"type": "committee_relevance", "explanation": "A reviewed direct mapping links the Armed Services seat to SIC 3721, and the seat is verified for the trade date."},
        {"type": "trade_size_anomaly", "explanation": "The trade is at the 100th percentile of 12 earlier trades by this member."},
        {"type": "disclosure_delay_signal", "explanation": "Disclosure came 59 days after the transaction, more than the 45-day threshold."},
        {"type": "excess_return_signal", "explanation": "The excess return is unknown because the 90-day price window is not available."},
    ],
    "limitations": "These public indicators do not establish possession or use of material non-public information, or any wrongdoing.",
}


def generic(facts):
    """A safe explanation for any trade's facts: no numbers, no committee names, no flag claims."""
    return Explanation(
        "Context for this trade is summarised from stored public records", "The signals below restate the values the deterministic engine stored for this trade.",
        [{"type": s["type"], "explanation": "Reported as stored; this explanation does not change it."} for s in facts["signals"]],
        "These public indicators do not establish what a member knew or intended.")


class FakeExplainer:
    def __init__(self, model=MODEL, answer=None, error=None, errors=None, tokens=(120, 80)):
        self.model, self.answer, self.error, self.errors, self.tokens = model, answer, error, list(errors or []), tokens
        self.requests_made = self.tokens_in = self.tokens_out = 0
        self.seen = []

    def explain(self, facts):
        self.requests_made += 1
        self.seen.append(facts)
        self.tokens_in += self.tokens[0]
        self.tokens_out += self.tokens[1]
        if self.errors:
            e = self.errors.pop(0)
            if e is not None:
                raise e
        if self.error:
            raise self.error
        if callable(self.answer):
            return self.answer(facts)
        return parse_explanation(self.answer) if self.answer else generic(facts)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """The real network transport is unreachable in this file: a test that tried a live OpenAI request would fail here. MockTransport clients are unaffected."""
    def blocked(self, request):
        raise AssertionError(f"live network request attempted: {request.url}")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)


@pytest.fixture
def flagged(session_factory):
    ids = seed(session_factory, dated_seat=True)
    run(session_factory)
    return ids


def service(sf, explainer, **kw):
    kw.setdefault("model", MODEL)
    return TradeContextExplanationService(sf, explainer, **kw)


def analyses(sf):
    with sf() as s:
        return list(s.scalars(select(TradeContextAnalysis).order_by(TradeContextAnalysis.id)))


def snapshot_context(sf):
    with sf() as s:
        cols = [c.name for c in TradeContext.__table__.columns]
        return [tuple(getattr(c, n) for n in cols) for c in s.scalars(select(TradeContext).order_by(TradeContext.id))]


def facts_of(sf, trade_id):
    with sf() as s:
        ctx = s.scalar(select(TradeContext).where(TradeContext.trade_id == trade_id))
        trade = s.get(Trade, trade_id)
        from poltracker.models import Politician, Security
        return build_facts(trade=trade, politician=s.get(Politician, trade.politician_id), security=s.get(Security, trade.security_id), context=ctx, evidence=ctx.evidence)


# --- what is sent --------------------------------------------------------------------------------------------------

def test_the_facts_are_this_trades_structured_context_and_nothing_else(session_factory, flagged):
    f = facts_of(session_factory, flagged["big"])
    assert set(f) == {"trade", "politician", "committee_evidence", "signals", "flag"}
    assert f["trade"]["ticker"] == "BA" and f["trade"]["sic_code"] == "3721" and f["trade"]["disclosed_amount_range_usd"] == {"min": 250001, "max": 500000}
    assert f["trade"]["transaction_date"] == "2026-02-20" and f["trade"]["disclosure_date"] == "2026-04-20"
    assert f["politician"] == {"name": "A B", "chamber": "house", "state": None, "district": None}
    [e] = f["committee_evidence"]
    assert e["committee"] == "Armed Services" and e["evidence_type"] == "reviewed_direct_mapping" and e["seat_held_on_transaction_date"] is True and e["seat_timing"] == "temporally_verified"
    assert e["mapping_review_status"] == "reviewed" and e["source_url"]
    sizes = {s["type"]: s for s in f["signals"]}
    assert sizes["trade_size_anomaly"]["percentile_among_this_members_own_earlier_trades"] == 100 and sizes["trade_size_anomaly"]["prior_trades_compared"] == 12
    assert sizes["disclosure_delay_signal"]["days_from_transaction_to_disclosure"] == 59 and sizes["excess_return_signal"]["value"] is None
    assert f["flag"]["flagged_for_contextual_review"] is True and f["flag"]["secondary_signal_count"] == 2
    blob = json.dumps(f)
    assert "C D" not in blob and "OPENAI" not in blob.upper()  # the other politician's rows and any key are not in the payload


def test_the_request_has_no_tools_does_not_store_and_uses_strict_structured_output(session_factory, flagged):
    sent = {}

    def handler(request):
        sent["body"], sent["auth"] = json.loads(request.content), request.headers["authorization"]
        return httpx.Response(200, json={"status": "completed", "usage": {"input_tokens": 10, "output_tokens": 5},
                                         "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(GOOD)}]}]})

    ex = OpenAIExplainer("sk-test-secret", "m1", httpx.Client(transport=httpx.MockTransport(handler)))
    res = service(session_factory, ex, model="m1").run()
    body = sent["body"]
    assert res.generated == 1 and body["model"] == "m1" and body["store"] is False and "tools" not in body and "tool_choice" not in body
    fmt = body["text"]["format"]
    assert fmt["type"] == "json_schema" and fmt["strict"] is True and fmt["schema"] == SCHEMA and body["instructions"] == SYSTEM
    assert sent["auth"] == "Bearer sk-test-secret" and "sk-test-secret" not in json.dumps(body) and (ex.tokens_in, ex.tokens_out) == (10, 5)
    assert SCHEMA["additionalProperties"] is False and set(SCHEMA["required"]) == {"headline", "summary", "signals", "limitations"}


def test_the_system_instruction_forbids_inference_external_facts_and_scores():
    for needle in ("Explain only the facts supplied", "external fact", "Do not infer intent", "material non-public information", "Timing and subject-matter proximity do not establish wrongdoing",
                   "probability, score or ranking", "observed facts", "interpretation"):
        assert needle in SYSTEM


# --- OpenAI responses: valid, malformed, refused, failed ---------------------------------------------------------

def explainer_for(handler):
    return OpenAIExplainer("sk-x", MODEL, httpx.Client(transport=httpx.MockTransport(handler)))


def reply(text=None, **extra):
    body = {"status": "completed", "usage": {"input_tokens": 7, "output_tokens": 3},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": text if text is not None else json.dumps(GOOD)}]}]}
    body.update(extra)
    return httpx.Response(200, json=body)


def test_a_valid_structured_response_is_parsed_validated_and_stored(session_factory, flagged):
    res = service(session_factory, explainer_for(lambda r: reply())).run()
    assert (res.selected, res.generated, res.calls, res.tokens_in, res.tokens_out) == (1, 1, 1, 7, 3)
    [a] = analyses(session_factory)
    assert a.headline == GOOD["headline"] and json.loads(a.signals_json) == GOOD["signals"] and a.generated_for == "flagged" and (a.input_tokens, a.output_tokens) == (7, 3)
    assert (a.model, a.prompt_version, a.context_version, a.mapping_version) == (MODEL, PROMPT_VERSION, tc.ENGINE_VERSION, "v1")


@pytest.mark.parametrize("response, why", [
    (lambda r: reply("this is not json"), "not valid JSON"),
    (lambda r: reply('{"headline": "x"}'), "unexpected fields"),
    (lambda r: reply(json.dumps({**GOOD, "suspicion_score": 0.9})), "unexpected fields"),
    (lambda r: reply(json.dumps({**GOOD, "signals": "none"})), "not a list"),
    (lambda r: reply(json.dumps({**GOOD, "headline": 5})), "not a string"),
    (lambda r: reply(json.dumps([GOOD])), "not an object"),
    (lambda r: httpx.Response(200, json={"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}]}), "refused"),
    (lambda r: httpx.Response(200, json={"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}, "output": []}), "incomplete"),
    (lambda r: httpx.Response(200, json={"status": "completed", "output": []}), "not valid JSON"),
    (lambda r: httpx.Response(200, json={"error": {"message": "x"}}), "carried an error"),
    (lambda r: httpx.Response(200, content=b"<html>"), "unexpected response shape"),
    (lambda r: httpx.Response(500, json={"error": "boom echoing the prompt"}), "HTTP 500"),
])
def test_malformed_refused_incomplete_and_failed_responses_are_errors_and_store_nothing(session_factory, flagged, response, why):
    res = service(session_factory, explainer_for(response)).run()
    assert res.generated == 0 and res.errors == 1 and analyses(session_factory) == []
    [item] = res.items
    assert item.status == "error" and why in item.reasons[0] and "echoing" not in item.reasons[0]


def test_a_network_failure_is_an_error_not_a_crash(session_factory, flagged):
    def boom(request):
        raise httpx.ConnectError("down")

    res = service(session_factory, explainer_for(boom)).run()
    assert res.errors == 1 and "network error" in res.items[0].reasons[0] and analyses(session_factory) == []


def test_an_authentication_failure_stops_the_run_instead_of_retrying_every_trade(session_factory, flagged):
    ex = FakeExplainer(error=ExplanationError("OpenAI API: HTTP 401", fatal=True))
    res = service(session_factory, ex).run(flagged_only=False)
    assert ex.requests_made == 1 and res.errors == 1 and res.aborted and "401" in res.aborted and res.over_limit == res.selected - 1


def test_one_failing_trade_does_not_stop_the_others(session_factory, flagged):
    ex = FakeExplainer(errors=[ExplanationError("OpenAI API: HTTP 500"), None])
    res = service(session_factory, ex).run(flagged_only=False, limit=2)
    assert (res.calls, res.errors, res.generated) == (2, 1, 1) and len(analyses(session_factory)) == 1


def test_a_missing_key_means_no_explainer_and_no_error_elsewhere(session_factory, flagged, monkeypatch, capsys):
    assert build_explainer(None, MODEL) is None and build_explainer("  ", MODEL) is None
    with pytest.raises(ExplanationError, match="OPENAI_API_KEY"):
        OpenAIExplainer("", MODEL)
    res = service(session_factory, None).run()
    assert res.aborted == "OPENAI_API_KEY is not set" and res.generated == 0 and analyses(session_factory) == []
    dry = service(session_factory, None).run(dry_run=True)  # a dry run needs no key
    assert dry.would_generate == 1 and dry.aborted is None
    monkeypatch.setattr(svc_mod, "get_settings", lambda: Settings(openai_api_key=None, database_url="sqlite://"))
    monkeypatch.setattr(svc_mod, "make_session_factory", lambda: session_factory)
    assert main([]) == 1 and "OPENAI_API_KEY is not set" in capsys.readouterr().out
    assert main(["--dry-run"]) == 0


# --- validation: invented evidence is rejected --------------------------------------------------------------------

def check(mutate, **kw):
    f = kw.pop("facts")
    answer = json.loads(json.dumps(GOOD))
    mutate(answer)
    validate_explanation(parse_explanation(answer), f, kw.get("known", frozenset({"armed services", "energy and commerce", "ways and means"})))


def test_the_good_explanation_validates(session_factory, flagged):
    check(lambda a: None, facts=facts_of(session_factory, flagged["big"]))


def reject(session_factory, flagged, mutate, fragment):
    with pytest.raises(ExplanationRejected) as exc:
        check(mutate, facts=facts_of(session_factory, flagged["big"]))
    assert any(fragment in r for r in exc.value.reasons), exc.value.reasons


def test_an_invented_signal_is_rejected(session_factory, flagged):
    reject(session_factory, flagged, lambda a: a["signals"].append({"type": "insider_trading_probability", "explanation": "high"}), "not a signal in this trade's context")


def test_a_signal_the_trade_does_not_have_is_rejected(session_factory, flagged):
    f = facts_of(session_factory, flagged["big"])
    f["signals"] = [s for s in f["signals"] if s["type"] != "excess_return_signal"]
    with pytest.raises(ExplanationRejected, match="excess_return_signal"):
        validate_explanation(parse_explanation(GOOD), f, frozenset())


def test_a_signal_explained_twice_is_rejected(session_factory, flagged):
    reject(session_factory, flagged, lambda a: a["signals"].append(a["signals"][0]), "explained twice")


@pytest.mark.parametrize("text", [
    "The member also sits on the Energy and Commerce Committee.",
    "As a member of the House Ways and Means Committee the member oversees taxation.",
    "The Committee on Financial Services held a related hearing.",
    "The member's seat on the Energy and Commerce panel is relevant.",  # no 'committee' word, but a known committee name
])
def test_an_invented_committee_is_rejected(session_factory, flagged, text):
    reject(session_factory, flagged, lambda a: a.__setitem__("summary", a["summary"] + " " + text), "committee")


def test_the_stored_committee_may_be_named_in_any_ordinary_form(session_factory, flagged):
    f = facts_of(session_factory, flagged["big"])
    for form in ("the House Armed Services Committee", "the Committee on Armed Services", "Armed Services Committee's jurisdiction"):
        a = json.loads(json.dumps(GOOD))
        a["signals"][0]["explanation"] = f"The member held a seat on {form} on the trade date."
        validate_explanation(parse_explanation(a), f, frozenset({"armed services", "energy and commerce"}))


@pytest.mark.parametrize("text, fragment", [
    ("The security returned 45.2% over the following 90 days.", "45.2"),
    ("The disclosed range was $9,000,000 to $10,000,000.", "9,000,000"),
    ("The disclosure was 120 days late.", "120"),
    ("It was the 37th percentile.", "37"),
])
def test_an_invented_number_is_rejected(session_factory, flagged, text, fragment):
    reject(session_factory, flagged, lambda a: a.__setitem__("summary", a["summary"] + " " + text), fragment)


@pytest.mark.parametrize("text", [
    "This looks like insider trading.",
    "The member was clearly tipped off.",
    "This is a suspicious trade by a corrupt politician.",
    "There is a high probability of wrongdoing.",
    "The member knew about the contract.",
    "This is illegal.",
])
def test_claims_of_wrongdoing_or_insider_knowledge_are_rejected(session_factory, flagged, text):
    reject(session_factory, flagged, lambda a: a.__setitem__("summary", a["summary"] + " " + text), "outside an explicit denial")


def test_an_explicit_denial_of_wrongdoing_is_allowed(session_factory, flagged):
    check(lambda a: a.__setitem__("limitations", "POLTRACKER does not establish insider trading, illegality or the use of material non-public information."), facts=facts_of(session_factory, flagged["big"]))


def test_talk_of_a_flag_on_an_unflagged_trade_is_rejected(session_factory, flagged):
    f = facts_of(session_factory, flagged["big"])
    f["flag"]["flagged_for_contextual_review"] = False
    with pytest.raises(ExplanationRejected, match="not flagged"):
        validate_explanation(parse_explanation(GOOD), f, frozenset())
    a = json.loads(json.dumps(GOOD))
    a["summary"] = "This trade is not flagged; this is an explanation on request, not a flag."
    validate_explanation(parse_explanation(a), f, frozenset())


def test_empty_or_oversized_text_is_rejected(session_factory, flagged):
    reject(session_factory, flagged, lambda a: a.__setitem__("headline", ""), "headline is empty")
    reject(session_factory, flagged, lambda a: a.__setitem__("headline", "x" * 400), "longer than")
    reject(session_factory, flagged, lambda a: a.__setitem__("signals", []), "no signal explanations")


def test_a_rejected_answer_is_never_stored_and_never_touches_the_flag(session_factory, flagged):
    before = snapshot_context(session_factory)
    bad = {**GOOD, "summary": "This was insider trading by the Energy and Commerce Committee member."}
    res = service(session_factory, FakeExplainer(answer=bad)).run()
    assert (res.rejected, res.generated) == (1, 0) and analyses(session_factory) == [] and res.items[0].reasons
    assert snapshot_context(session_factory) == before


# --- cache, force, invalidation, limits, selection ---------------------------------------------------------------

def test_a_valid_result_is_cached_and_a_rerun_makes_no_call(session_factory, flagged):
    ex = FakeExplainer(answer=GOOD)
    first = service(session_factory, ex).run()
    second = service(session_factory, ex).run()
    assert (first.generated, first.calls, second.cached, second.calls, second.generated) == (1, 1, 1, 0, 0) and ex.requests_made == 1 and len(analyses(session_factory)) == 1
    assert second.items[0].explanation["headline"] == GOOD["headline"]


def test_force_regenerates_in_place_and_keeps_one_row(session_factory, flagged):
    ex = FakeExplainer(answer=GOOD)
    service(session_factory, ex).run()
    [row] = analyses(session_factory)
    changed = {**GOOD, "headline": "A different but still valid headline about the aircraft-industry purchase"}
    res = service(session_factory, FakeExplainer(answer=changed)).run(force=True)
    [row2] = analyses(session_factory)
    assert res.generated == 1 and row2.id == row.id and row2.headline.startswith("A different")


def test_a_failed_forced_refresh_keeps_the_valid_cached_result(session_factory, flagged):
    service(session_factory, FakeExplainer(answer=GOOD)).run()
    res = service(session_factory, FakeExplainer(error=ExplanationError("OpenAI API: HTTP 500"))).run(force=True)
    assert res.errors == 1 and analyses(session_factory)[0].headline == GOOD["headline"]


def test_a_new_prompt_version_does_not_reuse_the_old_answer(session_factory, flagged, monkeypatch):
    service(session_factory, FakeExplainer(answer=GOOD)).run()
    monkeypatch.setattr(svc_mod, "PROMPT_VERSION", "99")
    ex = FakeExplainer(answer=GOOD)
    res = service(session_factory, ex).run()
    assert res.generated == 1 and ex.requests_made == 1 and sorted(a.prompt_version for a in analyses(session_factory)) == [PROMPT_VERSION, "99"]
    assert input_hash({"a": 1}, MODEL, "1") != input_hash({"a": 1}, MODEL, "99")


def test_a_new_model_does_not_reuse_the_old_answer(session_factory, flagged):
    service(session_factory, FakeExplainer(answer=GOOD)).run()
    res = service(session_factory, FakeExplainer(model="other", answer=GOOD), model="other").run()
    assert res.generated == 1 and sorted(a.model for a in analyses(session_factory)) == ["other", MODEL]


def test_a_new_context_version_does_not_reuse_the_old_answer(session_factory, flagged, monkeypatch):
    service(session_factory, FakeExplainer(answer=GOOD)).run()
    monkeypatch.setattr(tc, "ENGINE_VERSION", "9999.1")
    run(session_factory)  # the deterministic engine writes its own rows under the new version
    ex = FakeExplainer(answer=GOOD)
    res = service(session_factory, ex).run()
    assert res.generated == 1 and ex.requests_made == 1 and sorted(a.context_version for a in analyses(session_factory)) == ["2026.3", "9999.1"] and len(analyses(session_factory)) == 2


def test_changed_evidence_regenerates_and_replaces_the_stale_text(session_factory, flagged):
    service(session_factory, FakeExplainer(answer=GOOD)).run()
    with session_factory() as s:  # simulate the engine storing a different result for the same trade
        c = s.scalar(select(TradeContext).where(TradeContext.trade_id == flagged["big"]))
        c.disclosure_delay_days, c.result_digest = 70, "newdigest"
        s.commit()
    stale = service(session_factory, FakeExplainer(answer=GOOD)).run()  # the old text says 59 days; the stored fact is now 70, so it is not reused and not accepted again
    assert stale.rejected == 1 and analyses(session_factory)[0].context_digest != "newdigest"
    updated = {**GOOD, "summary": GOOD["summary"].replace("59 days", "70 days"), "signals": [dict(s, explanation=s["explanation"].replace("59", "70")) for s in GOOD["signals"]]}
    ex = FakeExplainer(answer=updated)
    res = service(session_factory, ex).run()
    [row] = analyses(session_factory)
    assert res.generated == 1 and ex.requests_made == 1 and row.context_digest == "newdigest" and "70 days" in row.summary


def test_the_call_limit_is_enforced_and_the_rest_are_reported_as_skipped(session_factory, flagged):
    ex = FakeExplainer()
    res = service(session_factory, ex, max_calls=3).run(flagged_only=False)
    assert res.selected == 14 and ex.requests_made == 3 and res.calls == 3 and res.generated == 3 and res.over_limit == 11
    assert service(session_factory, FakeExplainer(), max_calls=25).run(flagged_only=False, limit=2).calls == 2  # --limit overrides the configured cap
    service(session_factory, FakeExplainer()).run()  # cache the flagged trade
    zero = service(session_factory, FakeExplainer(), max_calls=0).run(trade_ids=[flagged["big"]])
    assert (zero.calls, zero.over_limit, zero.generated, zero.cached) == (0, 0, 0, 1)  # a cached result needs no call even at a zero limit
    fresh = service(session_factory, FakeExplainer(), max_calls=0).run(flagged_only=False)
    assert fresh.calls == 0 and fresh.generated == 0 and fresh.over_limit + fresh.cached == 14 and fresh.cached >= 1


def test_the_default_run_explains_flagged_trades_only(session_factory, flagged):
    ex = FakeExplainer()
    res = service(session_factory, ex).run()
    assert res.selected == 1 and ex.requests_made == 1 and ex.seen[0]["flag"]["flagged_for_contextual_review"] is True
    assert ex.seen[0]["trade"]["ticker"] == "BA"


def test_an_unflagged_trade_is_explained_only_on_explicit_request_and_labelled_manual(session_factory, flagged):
    with session_factory() as s:
        unflagged = s.scalars(select(TradeContext.trade_id).where(TradeContext.flagged_for_contextual_review.is_(False)).order_by(TradeContext.trade_id)).first()
    ex = FakeExplainer()
    res = service(session_factory, ex).run(trade_ids=[unflagged])
    assert res.generated == 1 and ex.seen[0]["flag"]["flagged_for_contextual_review"] is False
    [row] = analyses(session_factory)
    assert row.trade_id == unflagged and row.generated_for == "manual"
    assert service(session_factory, FakeExplainer()).run(ticker="KO").selected == 0  # a ticker filter alone stays flagged-only
    assert service(session_factory, FakeExplainer()).run(ticker="KO", flagged_only=False).selected == 12


def test_a_dry_run_sends_nothing_and_writes_nothing(session_factory, flagged):
    ex = FakeExplainer()
    res = service(session_factory, ex).run(dry_run=True, flagged_only=False, limit=4)
    assert ex.requests_made == 0 and res.would_generate == 4 and res.over_limit == 10 and analyses(session_factory) == [] and res.items[0].facts


def test_token_and_cost_accounting(session_factory, flagged):
    res = service(session_factory, FakeExplainer(tokens=(1000, 500)), input_usd_per_mtok=2.0, output_usd_per_mtok=8.0).run()
    assert (res.calls, res.tokens_in, res.tokens_out) == (1, 1000, 500) and res.estimated_cost_usd == pytest.approx(1000 / 1e6 * 2 + 500 / 1e6 * 8)
    assert "input tokens: 1,000" in res.to_text() and "output tokens: 500" in res.to_text()
    none = service(session_factory, FakeExplainer(), ).run(force=True)
    assert none.estimated_cost_usd is None and "not estimated" in none.to_text()  # no rate is assumed
    with session_factory() as s:
        assert s.scalar(select(TradeContextAnalysis.input_tokens)) == 120


# --- the deterministic engine stays authoritative ----------------------------------------------------------------

def test_the_explanation_run_never_changes_a_signal_or_the_flag(session_factory, flagged):
    before = snapshot_context(session_factory)
    with session_factory() as s:
        evidence_before = s.scalar(select(func.count()).select_from(TradeContextEvidence))
    # an explainer that *says* the trade is clean or not flagged cannot move the stored flag
    calm = {**GOOD, "summary": "The trade is not flagged and nothing here matters."}
    service(session_factory, FakeExplainer(answer=calm)).run(flagged_only=False, limit=14)
    service(session_factory, FakeExplainer(answer=GOOD)).run(force=True)
    assert snapshot_context(session_factory) == before
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(TradeContextEvidence)) == evidence_before
        assert s.scalar(select(func.count()).select_from(TradeContext).where(TradeContext.flagged_for_contextual_review.is_(True))) == 1


def test_the_service_source_never_constructs_edits_or_deletes_a_context_row():
    import re

    src = open(svc_mod.__file__).read()
    assert not re.search(r"\bTradeContext\(", src) and not re.search(r"\bctx\.\w+\s*=[^=]", src) and "setattr(ctx" not in src and "delete(" not in src


# --- API ----------------------------------------------------------------------------------------------------------

@pytest.fixture
def client(session_factory):
    def override():
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_the_api_returns_the_cached_explanation_as_an_optional_part_of_the_context(session_factory, flagged, client):
    assert client.get(f"/trades/{flagged['big']}").json()["context"]["ai_context"] is None  # nothing generated yet: deterministic context renders normally
    service(session_factory, FakeExplainer(answer=GOOD)).run()
    ctx = client.get(f"/trades/{flagged['big']}").json()["context"]
    ai = ctx["ai_context"]
    assert ai["headline"] == GOOD["headline"] and ai["summary"] == GOOD["summary"] and ai["signals"] == GOOD["signals"] and ai["limitations"] == GOOD["limitations"]
    assert ai["generated_for"] == "flagged" and ai["model"] == MODEL and ai["prompt_version"] == PROMPT_VERSION and ai["generated_at"]
    assert ctx["flagged_for_contextual_review"] is True and ctx["signals"]["committee_relevance"] is True  # the deterministic fields are the engine's, untouched


def test_the_api_works_with_no_key_and_no_analysis_anywhere(session_factory, flagged, client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    body = client.get("/trades", params={"limit": 50}).json()
    assert body["total"] == 14 and all(t["context"]["ai_context"] is None for t in body["items"] if t["context"])


def test_a_database_without_the_cache_table_still_serves_trades_and_the_cli_explains_itself(session_factory, flagged, client, monkeypatch, capsys):
    with session_factory() as s:
        s.execute(sa.text("drop table trade_context_analysis"))
        s.commit()
    body = client.get(f"/trades/{flagged['big']}").json()
    assert body["context"]["flagged_for_contextual_review"] is True and body["context"]["ai_context"] is None
    monkeypatch.setattr(svc_mod, "get_settings", lambda: Settings(openai_api_key=None, database_url="sqlite://"))
    monkeypatch.setattr(svc_mod, "make_session_factory", lambda: session_factory)
    assert main(["--dry-run"]) == 1 and "alembic upgrade head" in capsys.readouterr().out


def test_the_api_shows_a_manual_explanation_for_an_unflagged_trade_as_manual(session_factory, flagged, client):
    with session_factory() as s:
        tid = s.scalars(select(TradeContext.trade_id).where(TradeContext.flagged_for_contextual_review.is_(False)).order_by(TradeContext.trade_id)).first()
    service(session_factory, FakeExplainer()).run(trade_ids=[tid])
    ctx = client.get(f"/trades/{tid}").json()["context"]
    assert ctx["flagged_for_contextual_review"] is False and ctx["ai_context"]["generated_for"] == "manual"


def test_the_api_hides_an_explanation_once_the_context_it_explained_has_changed(session_factory, flagged, client):
    service(session_factory, FakeExplainer(answer=GOOD)).run()
    with session_factory() as s:
        c = s.scalar(select(TradeContext).where(TradeContext.trade_id == flagged["big"]))
        c.result_digest = "changed"
        s.commit()
    assert client.get(f"/trades/{flagged['big']}").json()["context"]["ai_context"] is None


def test_the_api_ignores_an_explanation_from_another_prompt_version(session_factory, flagged, client):
    service(session_factory, FakeExplainer(answer=GOOD)).run()
    with session_factory() as s:
        s.scalar(select(TradeContextAnalysis)).prompt_version = "0"
        s.commit()
    assert client.get(f"/trades/{flagged['big']}").json()["context"]["ai_context"] is None


# --- config and migration ------------------------------------------------------------------------------------------

def test_the_model_is_configurable_through_poltracker_trade_llm_model(monkeypatch):
    assert Settings(_env_file=None).trade_llm_model == "gpt-4o-mini" and Settings(_env_file=None).trade_llm_max_calls == 25
    monkeypatch.setenv("POLTRACKER_TRADE_LLM_MODEL", "some-other-model")
    monkeypatch.setenv("POLTRACKER_TRADE_LLM_MAX_CALLS", "5")
    monkeypatch.setenv("POLTRACKER_TRADE_LLM_INPUT_USD_PER_MTOK", "0.5")
    s = Settings(_env_file=None)
    assert (s.trade_llm_model, s.trade_llm_max_calls, s.trade_llm_input_usd_per_mtok, s.trade_llm_output_usd_per_mtok) == ("some-other-model", 5, 0.5, None)


def test_migration_0015_adds_only_the_cache_table_and_leaves_existing_data_untouched(db):
    engine, cfg = db
    command.upgrade(cfg, "0014")
    with engine.begin() as c:
        c.exec_driver_sql("insert into politicians (id, canonical_key, name, chamber, created_at) values (1, 'a', 'A', 'house', '2026-01-01')")
    before = set(sa.inspect(engine).get_table_names())
    command.upgrade(cfg, "head")
    assert set(sa.inspect(engine).get_table_names()) - before == {"trade_context_analysis"}
    with engine.connect() as c:
        assert c.exec_driver_sql("select count(*) from politicians").scalar() == 1 and c.exec_driver_sql("select version_num from alembic_version").scalar() == "0015"
    cols = {c["name"] for c in sa.inspect(engine).get_columns("trade_context_analysis")}
    assert {"trade_id", "context_version", "mapping_version", "prompt_version", "model", "input_hash", "headline", "summary", "signals_json", "limitations", "created_at"} <= cols
    command.downgrade(cfg, "0014")
    assert "trade_context_analysis" not in sa.inspect(engine).get_table_names()
    command.upgrade(cfg, "head")


def test_the_cache_identity_is_unique_per_trade_version_prompt_and_model(session_factory, flagged):
    service(session_factory, FakeExplainer(answer=GOOD)).run()
    [a] = analyses(session_factory)
    with session_factory() as s:
        s.add(TradeContextAnalysis(trade_id=a.trade_id, context_version=a.context_version, mapping_version=a.mapping_version, prompt_version=a.prompt_version, model=a.model,
                                   input_hash="x", context_digest="x", generated_for="flagged", headline="h", summary="s", signals_json="[]", limitations="l", created_at=a.created_at))
        with pytest.raises(sa.exc.IntegrityError):
            s.commit()


def test_a_negative_return_is_matched_by_magnitude_and_an_invented_one_still_fails(session_factory, flagged):
    f = facts_of(session_factory, flagged["big"])
    f["signals"][3].update(value=True, security_return_pct=-25.5, spy_return_pct=2.65, excess_return_pct_points=-28.15)
    a = json.loads(json.dumps(GOOD))
    a["signals"][3]["explanation"] = "The security's price fell 25.5% while SPY rose 2.65%, an excess return of -28.15 percentage points."
    validate_explanation(parse_explanation(a), f, frozenset())
    a["signals"][3]["explanation"] = a["signals"][3]["explanation"].replace("25.5%", "31%")
    with pytest.raises(ExplanationRejected, match="31"):
        validate_explanation(parse_explanation(a), f, frozenset())


# --- regression: a person's name in prose is not a committee (live validation, trade 328) -------------------------

KNOWN = frozenset({"armed services", "energy and commerce", "ways and means"})


def cisneros_facts(session_factory, flagged):
    f = facts_of(session_factory, flagged["big"])
    f["politician"]["name"] = "Gilbert Cisneros"
    f["trade"]["company_name"] = "AeroVironment, Inc. - Common Stock"
    return f


def with_text(text, field="explanation"):
    a = json.loads(json.dumps(GOOD))
    a["signals"][0]["explanation"] = text
    return parse_explanation(a)


@pytest.mark.parametrize("text", [
    "The seat reflects Cisneros's committee assignment on Armed Services.",  # the reported failure: the surname right before the word 'committee'
    "Gilbert Cisneros's committee seat was verified for the trade date.",
    "This links Cisneros' committee role to the aircraft industry.",
    "This links Cisneros’s committee role to the aircraft industry.",  # typographic apostrophe
    "AeroVironment's committee-relevant industry is aircraft.",
    "Cisneros committee context is verified.",  # no apostrophe at all: the member's own name words are never committee words
])
def test_a_politician_or_company_name_in_prose_is_not_a_committee(session_factory, flagged, text):
    validate_explanation(with_text(text), cisneros_facts(session_factory, flagged), KNOWN)


def test_the_stored_committee_still_passes_in_every_ordinary_form(session_factory, flagged):
    f = cisneros_facts(session_factory, flagged)
    for text in ("Cisneros held a seat on the House Armed Services Committee.", "Cisneros sat on the Committee on Armed Services on the trade date.",
                 "The Armed Services Committee's jurisdiction covers military aircraft."):
        validate_explanation(with_text(text), f, KNOWN)


def test_a_politician_name_and_a_stored_committee_in_one_explanation(session_factory, flagged):
    text = "Gilbert Cisneros held a seat on the Armed Services Committee; Cisneros's committee seat was verified for 2026-02-20, and Cisneros's Armed Services Committee seat maps to SIC 3721."
    validate_explanation(with_text(text), cisneros_facts(session_factory, flagged), KNOWN)


@pytest.mark.parametrize("text", [
    "Cisneros also sits on the Energy and Commerce Committee.",
    "Cisneros's Energy and Commerce Committee seat is relevant.",  # the member's name next to an invented committee does not hide it
    "Gilbert Cisneros's seat on the Ways and Means Committee is relevant.",
    "The Committee on Financial Services held a hearing.",
    "Cisneros's seat on the Energy and Commerce panel is relevant.",  # known committee named without the word 'committee'
])
def test_an_invented_committee_still_fails_even_next_to_the_members_name(session_factory, flagged, text):
    with pytest.raises(ExplanationRejected, match="committee"):
        validate_explanation(with_text(text), cisneros_facts(session_factory, flagged), KNOWN)


def test_a_name_word_that_is_also_a_committee_word_is_not_ignored(session_factory, flagged):
    f = cisneros_facts(session_factory, flagged)
    f["politician"]["name"] = "Alex Commerce"  # a surname that happens to be a committee word must not open a hole
    with pytest.raises(ExplanationRejected, match="committee"):
        validate_explanation(with_text("Alex sits on the Energy and Commerce Committee."), f, KNOWN)


def test_several_valid_committee_evidence_records_are_each_accepted_and_not_mixed(session_factory, flagged):
    f = cisneros_facts(session_factory, flagged)
    f["committee_evidence"].append({**f["committee_evidence"][0], "evidence_type": "reviewed_related_mapping", "committee": "Committee on Energy and Commerce", "subcommittee": "Subcommittee on Health"})
    ok = "Cisneros's committee seat on the Armed Services Committee is the direct match; the Committee on Energy and Commerce and its Subcommittee on Health are supporting context only."
    validate_explanation(with_text(ok), f, KNOWN)
    mixed = "Cisneros held a seat on the Armed Services and Health Committee."  # words from two different records do not make a committee
    with pytest.raises(ExplanationRejected, match="committee"):
        validate_explanation(with_text(mixed), f, KNOWN)
    with pytest.raises(ExplanationRejected, match="Ways and Means|ways"):
        validate_explanation(with_text("Cisneros also serves on the Ways and Means Committee."), f, KNOWN)


def test_the_instructions_ask_for_shares_and_spy_and_still_forbid_external_facts():
    assert "'shares' or 'the security'" in SYSTEM and "'stake'" in SYSTEM and "SPY" in SYSTEM and "no news" in SYSTEM and "Do not introduce any external fact" in SYSTEM
    assert PROMPT_VERSION == "3"  # the wording changed, so earlier cached explanations are not reused


def test_a_rejected_answer_is_kept_in_memory_for_diagnosis_but_never_stored(session_factory, flagged):
    bad = {**GOOD, "summary": GOOD["summary"] + " The member also sits on the Energy and Commerce Committee."}
    res = service(session_factory, FakeExplainer(answer=bad)).run()
    [item] = res.items
    assert item.status == "rejected" and item.rejected_answer["summary"].endswith("Committee.") and analyses(session_factory) == []


# --- prompt version 3: wording accuracy ------------------------------------------------------------------------------

def test_the_percentile_field_says_whose_trades_it_is_compared_against(session_factory, flagged):
    size = next(s for s in facts_of(session_factory, flagged["big"])["signals"] if s["type"] == "trade_size_anomaly")
    assert "percentile_among_this_members_own_earlier_trades" in size and "percentile_among_politicians_earlier_trades" not in size
    assert size["percentile_among_this_members_own_earlier_trades"] == 100 and size["prior_trades_compared"] == 12
    assert not any("politicians" in k for k in size)  # nothing in the field names invites a comparison with other politicians


def test_the_prompt_ties_the_percentile_to_the_same_member_and_forbids_other_comparisons():
    assert "against this same member's own earlier disclosed trades only" in SYSTEM
    assert "Never describe the comparison as being against other politicians or the broader market" in SYSTEM
    assert "the trade was at the 46th percentile of this member's own earlier disclosed trades" in SYSTEM


def test_the_prompt_rules_out_loose_percentile_wording():
    assert "'similar transactions'" in SYSTEM and "'normal'" in SYSTEM and "unless a supplied fact says so" in SYSTEM


def test_the_prompt_says_excess_return_is_in_percentage_points_not_percent():
    assert "percentage-point differences between the security return and the SPY return" in SYSTEM
    assert "Describe them as percentage points, not percent" in SYSTEM


def test_the_excess_return_facts_are_labelled_as_percentage_points(session_factory, flagged):
    ex = next(s for s in facts_of(session_factory, flagged["big"])["signals"] if s["type"] == "excess_return_signal")
    assert {"excess_return_pct_points", "direction_adjusted_excess_return_pct_points", "threshold_pct_points"} <= set(ex) and "security_return_pct" in ex and "spy_return_pct" in ex


def test_the_correct_same_member_wording_validates(session_factory, flagged):
    a = json.loads(json.dumps(GOOD))
    a["signals"][1]["explanation"] = "The trade was at the 100th percentile of this member's own earlier disclosed trades (12 compared), above the 90th percentile threshold."
    validate_explanation(parse_explanation(a), facts_of(session_factory, flagged["big"]), KNOWN)


def test_a_prompt_version_change_to_3_does_not_reuse_version_2_answers(session_factory, flagged, monkeypatch):
    monkeypatch.setattr(svc_mod, "PROMPT_VERSION", "2")
    service(session_factory, FakeExplainer(answer=GOOD)).run()
    monkeypatch.setattr(svc_mod, "PROMPT_VERSION", PROMPT_VERSION)
    ex = FakeExplainer(answer=GOOD)
    res = service(session_factory, ex).run()
    assert res.generated == 1 and ex.requests_made == 1 and sorted(a.prompt_version for a in analyses(session_factory)) == ["2", PROMPT_VERSION]
