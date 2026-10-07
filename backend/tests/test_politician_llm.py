"""LLM-assisted identity resolution: an untrusted suggestion that must pass every deterministic check."""

import json
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import func, select

from poltracker.enrich_politicians import enrich_politicians, review_queue
from poltracker.models import Politician, PoliticianLlmSuggestion
from poltracker.politician_llm import (
    AnthropicIdentityResolver, IdentityRequest, LLMError, LLMSuggestion, build_user_message, parse_suggestion,
)

from test_enrich_politicians import NOW, FakeProvider, official


class FakeLLM:
    model = "fake-model"

    def __init__(self, selected=None, confidence=0.97, explanation="Dan is a short form of Daniel.", alternates=(), error=None):
        self.answer = LLMSuggestion(selected, confidence, explanation, tuple(alternates), "fake-model")
        self.error, self.requests = error, []

    def resolve(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.answer


ROSTER = [
    official("C001120", "Dan", "Crenshaw"),
    official("D000399", "Lloyd", "Doggett"),
    official("S000001", "Pat", "Smith", state="TX"),
    official("S000002", "Pat", "Smith", state="OH"),
]


@pytest.fixture
def pols(session_factory):
    with session_factory() as s:
        rows = [
            Politician(canonical_key="house:danielcrenshaw", name="Daniel Crenshaw", chamber="house"),
            Politician(canonical_key="house:lloyddoggett", name="Lloyd Doggett", chamber="house"),
            Politician(canonical_key="house:patrickksmith", name="Patrick Smith", chamber="house", state="TX"),
            Politician(canonical_key="house:patsmith", name="Patrick Smith", chamber="house"),
        ]
        s.add_all(rows)
        s.commit()
        return {"crenshaw": rows[0].id, "doggett": rows[1].id, "smith_tx": rows[2].id, "smith_any": rows[3].id}


def run(sf, llm, roster=ROSTER, **kw):
    return enrich_politicians(sf, FakeProvider(roster), now=kw.pop("now", NOW), llm=llm, **kw)


def pol(sf, pid):
    with sf() as s:
        return s.get(Politician, pid)


def test_a_valid_suggestion_resolves_the_politician_and_stores_the_audit_trail(session_factory, pols):
    llm = FakeLLM("C001120")
    report = run(session_factory, llm, only_ids={pols["crenshaw"]})
    p = pol(session_factory, pols["crenshaw"])
    assert (p.bioguide_id, p.enrichment_status, p.enrichment_method, p.party, p.state) == ("C001120", "matched", "llm", "D", "TX")
    assert "LLM-assisted (fake-model, confidence 0.97)" in p.enrichment_note and "short form" in p.enrichment_note
    assert report.llm_resolved == [(pols["crenshaw"], "Daniel Crenshaw", "C001120")] and report.llm_calls == 1
    with session_factory() as s:
        row = s.scalar(select(PoliticianLlmSuggestion))
    assert (row.selected_bioguide_id, row.confidence, row.model, row.outcome, row.reason, row.politician_id) == (
        "C001120", 0.97, "fake-model", "accepted", None, pols["crenshaw"])
    assert row.explanation and row.decided_at == NOW and row.candidate_ids == "C001120"


def test_the_model_sees_only_the_name_chamber_and_same_surname_official_candidates(session_factory, pols):
    llm = FakeLLM("C001120")
    run(session_factory, llm, only_ids={pols["crenshaw"]})
    (req,) = llm.requests
    assert (req.name, req.chamber, req.state) == ("Daniel Crenshaw", "house", None)
    assert [m.bioguide_id for m in req.candidates] == ["C001120"]
    text = build_user_message(req)
    assert "C001120" in text and "D000399" not in text  # unrelated members are never sent


def test_a_hallucinated_bioguide_id_is_rejected_and_nothing_is_created(session_factory, pols):
    report = run(session_factory, FakeLLM("Z999999"), only_ids={pols["crenshaw"]})
    p = pol(session_factory, pols["crenshaw"])
    assert p.bioguide_id is None and p.enrichment_status == "unmatched" and "invented identifier" in p.enrichment_note
    assert not report.llm_resolved
    with session_factory() as s:
        assert s.scalar(select(func.count(Politician.id))) == 4
        assert s.scalar(select(PoliticianLlmSuggestion.outcome)) == "rejected"


def test_an_id_from_outside_the_candidates_is_rejected(session_factory, pols):
    run(session_factory, FakeLLM("D000399"), only_ids={pols["crenshaw"]})  # a real member, but not a candidate
    p = pol(session_factory, pols["crenshaw"])
    assert p.bioguide_id is None and "not among the candidates" in p.enrichment_note


def test_a_wrong_state_suggestion_is_rejected(session_factory, pols):
    run(session_factory, FakeLLM("S000002"), only_ids={pols["smith_tx"]})  # recorded as TX; the model picked the OH Smith
    p = pol(session_factory, pols["smith_tx"])
    assert p.bioguide_id is None and "from OH" in p.enrichment_note


def test_a_duplicate_id_already_owned_by_another_politician_is_rejected(session_factory, pols):
    with session_factory() as s:
        s.get(Politician, pols["doggett"]).bioguide_id = "C001120"  # someone else already holds it
        s.commit()
    run(session_factory, FakeLLM("C001120"), only_ids={pols["crenshaw"]})
    p = pol(session_factory, pols["crenshaw"])
    assert p.bioguide_id is None and "already belongs to politician" in p.enrichment_note


@pytest.mark.parametrize("confidence", [0.9, 0.5, None])
def test_a_confidence_that_does_not_exceed_the_threshold_is_rejected(session_factory, pols, confidence):
    run(session_factory, FakeLLM("C001120", confidence=confidence), only_ids={pols["crenshaw"]}, llm_min_confidence=0.9)
    p = pol(session_factory, pols["crenshaw"])
    assert p.bioguide_id is None and "does not exceed" in p.enrichment_note


def test_the_threshold_is_configurable(session_factory, pols):
    run(session_factory, FakeLLM("C001120", confidence=0.75), only_ids={pols["crenshaw"]}, llm_min_confidence=0.7)
    assert pol(session_factory, pols["crenshaw"]).bioguide_id == "C001120"


def test_two_valid_candidates_are_ambiguous_and_the_model_is_not_even_asked(session_factory, pols):
    llm = FakeLLM("S000001")
    report = run(session_factory, llm, only_ids={pols["smith_any"]})  # no state recorded: both Smiths remain valid
    p = pol(session_factory, pols["smith_any"])
    assert p.bioguide_id is None and "2 valid candidates" in p.enrichment_note
    assert llm.requests == [] and report.llm_calls == 0


def test_an_alternate_that_is_also_valid_makes_it_ambiguous(session_factory, pols):
    roster = [official("S000001", "Pat", "Smith", state="TX"), official("S000009", "Pat", "Smith", state="TX")]
    # both are valid, so this never reaches validation of alternates; check the guard directly instead
    from poltracker.politician_llm import validate_suggestion

    req = IdentityRequest("Patrick Smith", "house", "TX", None, tuple(roster[:1]))
    by_id = {m.bioguide_id: m for m in roster}
    verdict = validate_suggestion(LLMSuggestion("S000001", 0.99, "x", ("S000001",), "m"), req, by_id, {}, 1, 0.9)
    assert verdict.member is not None  # naming itself as an alternate is harmless
    req2 = IdentityRequest("Patrick Smith", "house", "TX", None, tuple(roster))
    assert validate_suggestion(LLMSuggestion("S000001", 0.99, "x", ("S000009",), "m"), req2, by_id, {}, 1, 0.9).member is None


def test_a_cached_suggestion_is_reused_and_still_revalidated(session_factory, pols):
    llm = FakeLLM("Z999999")  # rejected the first time
    run(session_factory, llm, only_ids={pols["crenshaw"]})
    assert len(llm.requests) == 1
    again = run(session_factory, llm, only_ids={pols["crenshaw"]}, force=True, now=NOW + timedelta(days=1))
    assert len(llm.requests) == 1 and again.llm_cached == 1 and again.llm_calls == 0  # not sent again
    with session_factory() as s:
        assert s.scalar(select(func.count(PoliticianLlmSuggestion.id))) == 1


def test_a_cached_acceptance_is_rechecked_against_current_data(session_factory, pols):
    llm = FakeLLM("C001120")
    run(session_factory, llm, only_ids={pols["crenshaw"]}, dry_run=False)
    with session_factory() as s:  # undo the match, and give the ID to someone else
        c = s.get(Politician, pols["crenshaw"])
        c.bioguide_id, c.enrichment_status, c.enrichment_method, c.party, c.state, c.district = None, "unmatched", None, None, None, None
        s.get(Politician, pols["doggett"]).bioguide_id = "C001120"
        s.commit()
    report = run(session_factory, llm, only_ids={pols["crenshaw"]}, force=True, now=NOW + timedelta(days=1))
    assert report.llm_cached == 1 and len(llm.requests) == 1
    assert pol(session_factory, pols["crenshaw"]).bioguide_id is None  # the cached "yes" no longer validates


def test_an_llm_outage_leaves_the_politician_unresolved_and_is_not_cached(session_factory, pols):
    report = run(session_factory, FakeLLM(error=LLMError("Anthropic API: HTTP 529")), only_ids={pols["crenshaw"]})
    assert report.llm_errors and pol(session_factory, pols["crenshaw"]).bioguide_id is None
    with session_factory() as s:
        assert s.scalar(select(func.count(PoliticianLlmSuggestion.id))) == 0


def test_the_model_is_never_asked_about_resolved_politicians(session_factory, pols):
    llm = FakeLLM("C001120")
    run(session_factory, llm)
    assert pol(session_factory, pols["doggett"]).enrichment_method == "exact_name+chamber"
    asked = {r.name for r in llm.requests}
    assert "Lloyd Doggett" not in asked
    run(session_factory, llm, now=NOW + timedelta(days=1), force=True)
    assert all(r.name != "Lloyd Doggett" for r in llm.requests)


def test_the_call_cap_per_run_is_respected(session_factory, pols):
    llm = FakeLLM("C001120")
    report = run(session_factory, llm, llm_max_calls=0, only_ids={pols["crenshaw"]})
    assert llm.requests == [] and "call limit" in pol(session_factory, pols["crenshaw"]).enrichment_note and report.llm_calls == 0


def test_no_llm_means_no_llm_stage(session_factory, pols):
    run(session_factory, None, only_ids={pols["crenshaw"]})
    p = pol(session_factory, pols["crenshaw"])
    assert p.enrichment_status == "unmatched" and "LLM" not in (p.enrichment_note or "")


def test_the_review_queue_lists_unresolved_politicians_with_the_llm_outcome(session_factory, pols):
    run(session_factory, FakeLLM("S000002"), only_ids={pols["smith_tx"], pols["crenshaw"]})
    queue = {r["id"]: r for r in review_queue(session_factory)}
    assert set(queue) == {pols["smith_tx"], pols["crenshaw"]} or pols["smith_tx"] in queue
    smith = queue[pols["smith_tx"]]
    assert smith["llm_outcome"] == "rejected" and smith["llm_selected"] == "S000002" and "OH" in smith["llm_reason"]


# --- the Anthropic client and the structured-output parser -------------------------------------------------

def tool_response(payload):
    return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}, {"type": "tool_use", "name": "report_identity", "input": payload}]})


def make_client(handler):
    return AnthropicIdentityResolver("test-key", "m", client=httpx.Client(transport=httpx.MockTransport(handler)))


REQ = IdentityRequest("Daniel Crenshaw", "house", None, None, (official("C001120", "Dan", "Crenshaw"),))


def test_the_client_sends_a_forced_tool_call_and_parses_the_structured_answer():
    seen = []

    def handler(req):
        seen.append(req)
        return tool_response({"selected_bioguide_id": "c001120", "confidence": 0.95, "explanation": "same", "alternate_candidates": []})

    s = make_client(handler).resolve(REQ)
    assert (s.selected_bioguide_id, s.confidence, s.explanation) == ("C001120", 0.95, "same")
    sent = json.loads(seen[0].content)
    assert sent["tool_choice"] == {"type": "tool", "name": "report_identity"} and sent["temperature"] == 0
    assert seen[0].headers["x-api-key"] == "test-key" and "C001120" in sent["messages"][0]["content"]


@pytest.mark.parametrize("payload", [
    "text", {"selected_bioguide_id": 5, "confidence": 0.9, "explanation": "", "alternate_candidates": []},
    {"selected_bioguide_id": None, "confidence": 1.5, "explanation": "", "alternate_candidates": []},
    {"selected_bioguide_id": None, "confidence": "high", "explanation": "", "alternate_candidates": []},
    {"selected_bioguide_id": None, "confidence": 0.9, "explanation": "", "alternate_candidates": "x"},
])
def test_malformed_structured_output_is_an_error_not_a_guess(payload):
    with pytest.raises(LLMError):
        parse_suggestion(payload, "m")


@pytest.mark.parametrize("response", [httpx.Response(500), httpx.Response(401, json={"error": "bad key test-key"}),
                                       httpx.Response(200, json={"content": [{"type": "text", "text": "no tool"}]}),
                                       httpx.Response(200, content=b"<html>")])
def test_api_failures_become_llm_errors_without_leaking_the_key(response):
    with pytest.raises(LLMError) as exc:
        make_client(lambda r: response).resolve(REQ)
    assert "test-key" not in str(exc.value)


def test_a_network_error_becomes_an_llm_error():
    def boom(req):
        raise httpx.ConnectError("down", request=req)

    with pytest.raises(LLMError, match="network error"):
        make_client(boom).resolve(REQ)


# --- the OpenAI client (same contract as the Anthropic one) ---------------------------------------------------

from poltracker.politician_llm import OpenAIIdentityResolver


def openai_client(handler):
    return OpenAIIdentityResolver("test-key", "gpt-test", client=httpx.Client(transport=httpx.MockTransport(handler)))


def chat_response(content, **message):
    return httpx.Response(200, json={"choices": [{"message": {"content": content, **message}}], "usage": {"prompt_tokens": 600, "completion_tokens": 90}})


def test_the_openai_client_sends_a_strict_schema_and_parses_the_answer_and_counts_tokens():
    seen = []

    def handler(req):
        seen.append(req)
        return chat_response(json.dumps({"selected_bioguide_id": "c001120", "confidence": 0.96, "explanation": "same", "alternate_candidates": []}))

    client = openai_client(handler)
    s = client.resolve(REQ)
    assert (s.selected_bioguide_id, s.confidence, s.model) == ("C001120", 0.96, "gpt-test")
    sent = json.loads(seen[0].content)
    assert sent["response_format"]["json_schema"]["strict"] is True and sent["temperature"] == 0
    assert seen[0].headers["authorization"] == "Bearer test-key" and "C001120" in sent["messages"][1]["content"]
    assert (client.tokens_in, client.tokens_out) == (600, 90)


@pytest.mark.parametrize("response", [
    httpx.Response(429), httpx.Response(401, json={"error": {"message": "bad key test-key"}}),
    httpx.Response(200, json={"choices": []}), httpx.Response(200, content=b"<html>"),
    chat_response("not json"), chat_response(None, refusal="I can't help with that"),
    chat_response(json.dumps({"selected_bioguide_id": None, "confidence": 3, "explanation": "", "alternate_candidates": []})),
])
def test_openai_failures_and_malformed_answers_become_llm_errors_without_the_key(response):
    with pytest.raises(LLMError) as exc:
        openai_client(lambda r: response).resolve(REQ)
    assert "test-key" not in str(exc.value)


def test_an_openai_network_error_becomes_an_llm_error():
    def boom(req):
        raise httpx.ConnectError("down", request=req)

    with pytest.raises(LLMError, match="network error"):
        openai_client(boom).resolve(REQ)


def test_the_trace_records_what_the_model_said_even_when_it_is_rejected(session_factory, pols):
    report = run(session_factory, FakeLLM("Z999999", 0.99, "made it up"), only_ids={pols["crenshaw"]})
    (t,) = report.llm_trace
    assert (t["selected"], t["confidence"], t["explanation"], t["accepted"], t["cached"]) == ("Z999999", 0.99, "made it up", False, False)
    assert "invented identifier" in t["reason"] and t["candidates"] == [("Dan Crenshaw", "C001120", "TX")]
