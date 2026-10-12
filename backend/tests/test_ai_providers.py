"""In-app AI providers: Keychain-backed keys, the provider abstraction (OpenAI and Claude), on-demand and bulk generation, caching per provider/model, and the guarantee that
the AI explains and never decides. No test makes a live request and none touches the real Keychain."""

import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from poltracker.ai.keystore import SERVICE, KeyringSecretStore, MemorySecretStore, SecretStoreError, clean_key, mask_key
from poltracker.ai.providers import PROVIDERS, AnthropicExplanationProvider, build_provider
from poltracker.api.main import create_app, get_session
from poltracker.config import Settings
from poltracker.desktop.app import create_desktop_app
from poltracker.models import AppPreference, Base, TradeContext, TradeContextAnalysis
from poltracker.trade_context_llm import (
    SYSTEM, AIExplanationProvider, ExplanationError, OpenAIExplanationProvider, build_facts, parse_explanation,
)

from test_trade_context import run, seed  # noqa: F401
from test_trade_context_llm import GOOD, facts_of, snapshot_context  # noqa: F401

OPENAI_KEY = "sk-test-OPENAI-0123456789abcdef-1234"
CLAUDE_KEY = "sk-ant-test-CLAUDE-0123456789abcdef-5678"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(self, request):
        raise AssertionError(f"live network request attempted: {request.url}")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)


class Remote:
    """A scripted stand-in for both providers' HTTP APIs. Records every request."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.answer = GOOD
        self.status = 200
        self.raises: Exception | None = None
        self.raw_text: str | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.raises:
            raise self.raises
        if self.status != 200:
            return httpx.Response(self.status, json={"error": {"message": "echo " + request.headers.get("authorization", "") + request.headers.get("x-api-key", "")}})
        if request.method == "GET":
            return httpx.Response(200, json={"data": []})
        text = self.raw_text if self.raw_text is not None else json.dumps(self.answer)
        if "anthropic" in str(request.url):
            return httpx.Response(200, json={"type": "message", "stop_reason": "end_turn", "usage": {"input_tokens": 11, "output_tokens": 7}, "content": [{"type": "text", "text": text}]})
        return httpx.Response(200, json={"status": "completed", "usage": {"input_tokens": 10, "output_tokens": 5},
                                         "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]})

    def factory(self, provider, key, model):
        return build_provider(provider, key, model, httpx.Client(transport=httpx.MockTransport(self.handler)))

    def calls(self, method="POST"):
        return [r for r in self.requests if r.method == method]


@pytest.fixture
def remote():
    return Remote()


@pytest.fixture
def secrets():
    return MemorySecretStore()


@pytest.fixture
def flagged(session_factory):
    ids = seed(session_factory, dated_seat=True)
    run(session_factory)
    return ids


@pytest.fixture
def desktop(session_factory, secrets, remote, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<title>x</title>")
    app = create_desktop_app(frontend_dir=dist, settings=Settings(_env_file=None), enable_refresh=False, ai_secrets=secrets, ai_provider_factory=remote.factory,
                             ai_session_factory=session_factory)
    api = next(r.app for r in app.routes if getattr(r, "path", None) == "/api")

    def override():
        with session_factory() as s:
            yield s

    api.dependency_overrides[get_session] = override
    client = TestClient(app, base_url="http://127.0.0.1")
    client.app_obj = app
    return client


def save_key(c, provider="openai", key=OPENAI_KEY):
    return c.post("/api/ai/key", json={"provider": provider, "api_key": key})


def select_provider(c, provider, model=None):
    body = {"provider": provider, **({"model": model} if model else {})}
    return c.put("/api/ai/provider", json=body)


def analyses(sf):
    with sf() as s:
        return list(s.scalars(select(TradeContextAnalysis).order_by(TradeContextAnalysis.id)))


# --- key storage ---------------------------------------------------------------------------------------------------

class FakeKeychain:
    priority = 5

    def __init__(self):
        self.items = {}

    def get_password(self, service, account):
        return self.items.get((service, account))

    def set_password(self, service, account, secret):
        self.items[(service, account)] = secret

    def delete_password(self, service, account):
        del self.items[(service, account)]


def test_the_keychain_store_uses_one_item_per_provider_under_the_poltracker_service():
    kc = FakeKeychain()
    store = KeyringSecretStore(backend=kc)
    assert SERVICE == "com.roamingwizards.poltracker.ai"
    assert store.get("openai") is None and store.delete("openai") is False
    store.set("openai", "k1")
    store.set("anthropic", "k2")
    store.set("openai", "k3")  # replace
    assert kc.items == {(SERVICE, "openai"): "k3", (SERVICE, "anthropic"): "k2"}
    assert store.delete("openai") is True and store.get("openai") is None and store.get("anthropic") == "k2"


def test_without_a_secure_backend_saving_fails_instead_of_falling_back_to_a_file():
    class Insecure(FakeKeychain):
        priority = 0

    store = KeyringSecretStore(backend=Insecure())
    for call in (lambda: store.set("openai", "k"), lambda: store.get("openai"), lambda: store.delete("openai")):
        with pytest.raises(SecretStoreError):
            call()


def test_key_cleaning_and_masking_never_reveal_the_key():
    assert clean_key("  sk-abc123  ") == "sk-abc123"
    for bad in ("", "   ", "has space", "tab\tkey", "ключ", "x" * 500, None, 5):
        with pytest.raises(ValueError) as e:
            clean_key(bad)
        assert "has space" not in str(e.value)
    assert mask_key(OPENAI_KEY) == "sk-••••••••1234" and OPENAI_KEY[3:-4] not in mask_key(OPENAI_KEY)
    assert mask_key("short") == "••••••••"


def test_save_replace_remove_and_configured_state(desktop, secrets):
    s = desktop.get("/api/ai/settings").json()
    assert s["provider"] == "openai" and s["configured"] is False and all(not p["configured"] for p in s["providers"])
    r = save_key(desktop)
    assert r.status_code == 200
    s = r.json()
    openai = next(p for p in s["providers"] if p["id"] == "openai")
    assert s["configured"] is True and openai["configured"] and openai["masked"] == "sk-••••••••1234"
    assert secrets.get("openai") == OPENAI_KEY  # in the (fake) keychain
    save_key(desktop, key="sk-REPLACED-0000000000-9999")
    assert secrets.get("openai") == "sk-REPLACED-0000000000-9999"
    assert next(p for p in desktop.get("/api/ai/settings").json()["providers"] if p["id"] == "openai")["masked"].endswith("9999")
    r = desktop.delete("/api/ai/key", params={"provider": "openai"})
    assert r.status_code == 200 and r.json()["configured"] is False and secrets.get("openai") is None


def test_the_key_is_never_returned_by_any_response(desktop):
    texts = [save_key(desktop).text, desktop.get("/api/ai/settings").text, select_provider(desktop, "openai").text, desktop.post("/api/ai/test", json={}).text]
    texts.append(desktop.post("/api/ai/key", json={"provider": "openai", "api_key": "bad key with spaces"}).text)
    texts.append(desktop.post("/api/ai/key", json={"provider": "nope", "api_key": OPENAI_KEY}).text)
    texts.append(desktop.post("/api/ai/key", content=b'["' + OPENAI_KEY.encode() + b'"]', headers={"content-type": "application/json"}).text)
    texts.append(desktop.post("/api/ai/key", content=b'{"api_key": "' + OPENAI_KEY.encode(), headers={"content-type": "application/json"}).text)
    for t in texts:
        assert OPENAI_KEY not in t and OPENAI_KEY[3:-4] not in t and "bad key with spaces" not in t


def test_the_key_is_not_written_to_sqlite_or_preferences(desktop, session_factory):
    save_key(desktop)
    save_key(desktop, "anthropic", CLAUDE_KEY)
    select_provider(desktop, "anthropic", "claude-sonnet-5-5")
    with session_factory() as s:
        dump = []
        for table in Base.metadata.sorted_tables:
            dump += [str(tuple(r)) for r in s.execute(table.select())]
        pref = s.get(AppPreference, "ai_settings")
        assert json.loads(pref.value_json) == {"provider": "anthropic", "models": {"anthropic": "claude-sonnet-5-5"}}
    blob = "\n".join(dump)
    for key in (OPENAI_KEY, CLAUDE_KEY):
        assert key not in blob and key[3:-4] not in blob


def test_the_key_is_not_logged_or_printed(desktop, flagged, remote, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    save_key(desktop)
    desktop.post("/api/ai/test", json={})
    desktop.post(f"/api/trades/{flagged['big']}/ai-context/generate", json={})
    remote.status = 401
    desktop.post("/api/ai/test", json={})
    desktop.post(f"/api/trades/{flagged['big']}/ai-context/generate", json={"regenerate": True})
    out = capsys.readouterr()
    for text in (caplog.text, out.out, out.err):
        assert OPENAI_KEY not in text and OPENAI_KEY[3:-4] not in text


def test_a_keychain_failure_is_reported_cleanly(desktop, secrets):
    def boom(*a):
        raise SecretStoreError("Could not save the key to the system keychain.")
    secrets.set = boom
    r = save_key(desktop)
    assert r.status_code == 503 and r.json()["detail"]["code"] == "keychain_unavailable" and OPENAI_KEY not in r.text


def test_provider_and_model_choices_are_validated_and_persist(desktop):
    assert select_provider(desktop, "nope").status_code == 400
    assert select_provider(desktop, "anthropic", "bad model!").status_code == 400
    s = select_provider(desktop, "anthropic").json()
    assert s["provider"] == "anthropic" and s["model"] == PROVIDERS["anthropic"].default_model
    assert select_provider(desktop, "anthropic", "claude-sonnet-5-5").json()["model"] == "claude-sonnet-5-5"
    assert desktop.put("/api/ai/provider", json={"provider": "anthropic", "model": ""}).json()["model"] == PROVIDERS["anthropic"].default_model
    assert desktop.get("/api/ai/settings").json()["provider"] == "anthropic"  # read back from storage: survives a restart


def test_other_websites_cannot_use_the_local_endpoints(desktop):
    assert desktop.post("/api/ai/key", json={"provider": "openai", "api_key": OPENAI_KEY}, headers={"origin": "https://evil.example"}).status_code == 403
    assert desktop.post("/api/ai/key", content=json.dumps({"provider": "openai", "api_key": OPENAI_KEY}), headers={"content-type": "text/plain"}).status_code == 415
    assert desktop.delete("/api/ai/key", params={"provider": "openai"}, headers={"origin": "https://evil.example"}).status_code == 403
    assert desktop.get("/api/ai/settings").json()["configured"] is False
    assert desktop.post("/api/ai/key", json={"provider": "openai", "api_key": OPENAI_KEY}, headers={"origin": "http://127.0.0.1:8765"}).status_code == 200


# --- providers -----------------------------------------------------------------------------------------------------

def mock_client(remote):
    return httpx.Client(transport=httpx.MockTransport(remote.handler))


def test_both_providers_implement_the_abstraction():
    for spec in PROVIDERS.values():
        assert issubclass(spec.cls, AIExplanationProvider)
    p = OpenAIExplanationProvider("k", "m1")
    q = AnthropicExplanationProvider("k", "m2")
    assert (p.provider_name, p.model_name, q.provider_name, q.model_name) == ("openai", "m1", "anthropic", "m2")


def test_both_providers_receive_the_same_facts_and_instructions_and_use_no_tools(session_factory, flagged, remote):
    facts = facts_of(session_factory, flagged["big"])
    OpenAIExplanationProvider("k-o", "m1", mock_client(remote)).generate_trade_explanation(facts)
    AnthropicExplanationProvider("k-a", "m2", mock_client(remote)).generate_trade_explanation(facts)
    o, a = (json.loads(r.content) for r in remote.calls())
    assert "tools" not in o and "tools" not in a and "tool_choice" not in o and "tool_choice" not in a
    assert o["store"] is False
    assert o["input"] == a["messages"][0]["content"] and a["messages"] == [{"role": "user", "content": o["input"]}]
    assert json.loads(o["input"].split("\n", 1)[1]) == json.loads(json.dumps(facts, default=str))
    assert o["instructions"] == SYSTEM and a["system"].startswith(SYSTEM)
    auth = {str(r.url): r.headers for r in remote.calls()}
    assert auth["https://api.openai.com/v1/responses"]["authorization"] == "Bearer k-o"
    assert auth["https://api.anthropic.com/v1/messages"]["x-api-key"] == "k-a" and auth["https://api.anthropic.com/v1/messages"]["anthropic-version"]


def test_both_providers_return_the_same_normalized_schema(session_factory, flagged, remote):
    facts = facts_of(session_factory, flagged["big"])
    a = OpenAIExplanationProvider("k", "m", mock_client(remote)).generate_trade_explanation(facts)
    remote.raw_text = "```json\n" + json.dumps(GOOD) + "\n```"  # Claude sometimes fences its JSON
    b = AnthropicExplanationProvider("k", "m", mock_client(remote)).generate_trade_explanation(facts)
    assert a == b == parse_explanation(GOOD)


@pytest.mark.parametrize("cls", [OpenAIExplanationProvider, AnthropicExplanationProvider])
@pytest.mark.parametrize("status,code", [(401, "invalid_key"), (403, "invalid_key"), (429, "rate_limited"), (500, "unavailable"), (529, "unavailable"), (400, "error")])
def test_provider_http_failures_are_classified_and_leak_nothing(cls, status, code, session_factory, flagged, remote):
    facts = facts_of(session_factory, flagged["big"])
    remote.status = status
    p = cls("sk-SECRET-KEY-VALUE", "m", mock_client(remote))
    for call in (lambda: p.generate_trade_explanation(facts), p.validate_credentials):
        with pytest.raises(ExplanationError) as e:
            call()
        assert e.value.code == code and e.value.fatal == (code == "invalid_key")
        assert "SECRET-KEY" not in str(e.value) and "echo" not in str(e.value) and "Bearer" not in str(e.value)


@pytest.mark.parametrize("cls", [OpenAIExplanationProvider, AnthropicExplanationProvider])
def test_network_timeout_and_malformed_failures(cls, session_factory, flagged, remote):
    facts = facts_of(session_factory, flagged["big"])
    p = cls("sk-SECRET-KEY-VALUE", "m", mock_client(remote))
    remote.raises = httpx.ConnectError("no route", request=httpx.Request("POST", "https://x"))
    with pytest.raises(ExplanationError) as e:
        p.generate_trade_explanation(facts)
    assert e.value.code == "network" and "SECRET" not in str(e.value)
    remote.raises = httpx.ReadTimeout("slow", request=httpx.Request("POST", "https://x"))
    with pytest.raises(ExplanationError) as e:
        p.generate_trade_explanation(facts)
    assert e.value.code == "timeout"
    remote.raises = None
    for raw in ("not json at all", json.dumps({"headline": "only"}), json.dumps([1, 2])):
        remote.raw_text = raw
        with pytest.raises(ExplanationError) as e:
            p.generate_trade_explanation(facts)
        assert e.value.code == "malformed"


def test_claude_cut_off_or_refused_answers_are_errors(session_factory, flagged):
    facts = facts_of(session_factory, flagged["big"])
    for stop, code in (("max_tokens", "malformed"), ("refusal", "refused")):
        def handler(request, stop=stop):
            return httpx.Response(200, json={"type": "message", "stop_reason": stop, "content": [{"type": "text", "text": json.dumps(GOOD)}], "usage": {}})
        p = AnthropicExplanationProvider("k", "m", httpx.Client(transport=httpx.MockTransport(handler)))
        with pytest.raises(ExplanationError) as e:
            p.generate_trade_explanation(facts)
        assert e.value.code == code


def test_the_connection_test_spends_no_tokens(desktop, remote):
    save_key(desktop)
    r = desktop.post("/api/ai/test", json={}).json()
    assert r == {"ok": True, "code": None, "message": "Connected to OpenAI."}
    assert [(q.method, str(q.url)) for q in remote.requests] == [("GET", "https://api.openai.com/v1/models")]
    remote.status = 401
    r = desktop.post("/api/ai/test", json={}).json()
    assert r["ok"] is False and r["code"] == "invalid_key" and OPENAI_KEY not in json.dumps(r)
    assert desktop.post("/api/ai/test", json={"provider": "anthropic"}).json()["code"] == "not_configured"


# --- generation ----------------------------------------------------------------------------------------------------

def trade_ai(c, trade_id):
    return c.get(f"/api/trades/{trade_id}").json()["context"]["ai_context"]


def generate(c, trade_id, **body):
    return c.post(f"/api/trades/{trade_id}/ai-context/generate", json=body)


def test_opening_a_trade_never_calls_a_provider(desktop, flagged, remote):
    save_key(desktop)
    assert trade_ai(desktop, flagged["big"]) is None
    desktop.get("/api/trades")
    desktop.get("/api/ai/settings")
    assert remote.requests == []


def test_generate_on_demand_caches_and_shows_provider_and_model(desktop, flagged, remote, session_factory):
    save_key(desktop)
    r = generate(desktop, flagged["big"])
    assert r.status_code == 200
    body = r.json()
    assert body["from_cache"] is False and body["ai_context"]["provider"] == "openai" and body["ai_context"]["model"] == "gpt-4o-mini"
    assert body["ai_context"]["headline"] == GOOD["headline"] and body["ai_context"]["generated_for"] == "flagged"
    assert len(remote.calls()) == 1 and len(analyses(session_factory)) == 1
    shown = trade_ai(desktop, flagged["big"])  # visible without a restart or another call
    assert shown["provider"] == "openai" and shown["model"] == "gpt-4o-mini" and shown["generated_at"]
    again = generate(desktop, flagged["big"]).json()  # cache hit: no second request
    assert again["from_cache"] is True and len(remote.calls()) == 1


def test_regenerate_asks_the_provider_again_and_replaces_only_the_same_provider_row(desktop, flagged, remote, session_factory):
    save_key(desktop)
    generate(desktop, flagged["big"])
    first = analyses(session_factory)[0].created_at
    r = generate(desktop, flagged["big"], regenerate=True)
    assert r.status_code == 200 and r.json()["from_cache"] is False and len(remote.calls()) == 2
    rows = analyses(session_factory)
    assert len(rows) == 1 and rows[0].created_at >= first


def test_a_failed_regeneration_keeps_the_previous_accepted_explanation(desktop, flagged, remote):
    save_key(desktop)
    generate(desktop, flagged["big"])
    remote.status = 429
    r = generate(desktop, flagged["big"], regenerate=True)
    assert r.status_code == 429 and r.json()["detail"]["code"] == "rate_limited"
    assert trade_ai(desktop, flagged["big"])["headline"] == GOOD["headline"]


def test_each_provider_and_model_has_its_own_cached_explanation(desktop, flagged, remote, session_factory):
    save_key(desktop)
    save_key(desktop, "anthropic", CLAUDE_KEY)
    generate(desktop, flagged["big"])
    select_provider(desktop, "anthropic")
    assert trade_ai(desktop, flagged["big"])["provider"] == "openai"  # the earlier one stays visible; it is not presented as Claude's
    n = len(remote.calls())
    claude = generate(desktop, flagged["big"]).json()
    assert claude["from_cache"] is False and claude["ai_context"]["provider"] == "anthropic" and claude["ai_context"]["model"] == PROVIDERS["anthropic"].default_model
    assert len(remote.calls()) == n + 1 and str(remote.calls()[-1].url).startswith("https://api.anthropic.com/")
    assert {(a.provider, a.model) for a in analyses(session_factory)} == {("openai", "gpt-4o-mini"), ("anthropic", "claude-haiku-5-5")}
    assert trade_ai(desktop, flagged["big"])["provider"] == "anthropic"
    select_provider(desktop, "openai")
    assert trade_ai(desktop, flagged["big"])["provider"] == "openai" and len(analyses(session_factory)) == 2  # nothing was deleted
    select_provider(desktop, "anthropic", "claude-sonnet-5-5")  # a different model is a separate cache entry too
    assert generate(desktop, flagged["big"]).json()["from_cache"] is False and len(analyses(session_factory)) == 3


def test_a_rejected_answer_is_never_stored_or_shown(desktop, flagged, remote, session_factory):
    save_key(desktop)
    bad = {**GOOD, "summary": "The member used insider information, which is why Pentagon Oversight Committee approved 12345 shares."}
    remote.answer = bad
    r = generate(desktop, flagged["big"])
    assert r.status_code == 422 and r.json()["detail"] == {"code": "validation_rejected", "message": "AI explanation could not be generated from the available evidence."}
    assert "insider" not in r.text and "Pentagon" not in r.text and "12345" not in r.text
    assert analyses(session_factory) == [] and trade_ai(desktop, flagged["big"]) is None


def test_claude_output_goes_through_the_same_validation(desktop, flagged, remote, session_factory):
    save_key(desktop, "anthropic", CLAUDE_KEY)
    select_provider(desktop, "anthropic")
    remote.answer = {**GOOD, "headline": "This was suspicious trading by the member"}
    assert generate(desktop, flagged["big"]).status_code == 422 and analyses(session_factory) == []


def test_malformed_provider_output_is_a_clean_error(desktop, flagged, remote):
    save_key(desktop)
    remote.raw_text = "<<<garbage"
    r = generate(desktop, flagged["big"])
    assert r.status_code == 502 and r.json()["detail"]["code"] == "malformed" and "garbage" not in r.text


def test_generating_never_changes_a_signal_or_the_flag(desktop, flagged, remote, session_factory):
    save_key(desktop)
    before = snapshot_context(session_factory)
    generate(desktop, flagged["big"])
    generate(desktop, flagged["big"], regenerate=True)
    remote.answer = {**GOOD, "summary": "the member knew"}
    generate(desktop, flagged["big"], regenerate=True)
    assert snapshot_context(session_factory) == before
    with session_factory() as s:
        assert s.scalar(select(TradeContext).where(TradeContext.trade_id == flagged["big"])).flagged_for_contextual_review is True


def test_without_a_saved_key_generation_says_so_and_calls_nothing(desktop, flagged, remote):
    r = generate(desktop, flagged["big"])
    assert r.status_code == 409 and r.json()["detail"]["code"] == "not_configured" and remote.requests == []


def test_an_unflagged_trade_is_refused_unless_explicitly_requested_and_is_labelled_manual(desktop, flagged, remote, session_factory):
    save_key(desktop)
    with session_factory() as s:
        other = s.scalar(select(TradeContext).where(TradeContext.flagged_for_contextual_review.is_(False)).order_by(TradeContext.trade_id)).trade_id
    r = generate(desktop, other)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "not_flagged" and remote.requests == []
    types = ["committee_relevance", "trade_size_anomaly", "disclosure_delay_signal", "excess_return_signal"]
    remote.answer = {"headline": "Context for this trade is summarised from stored public records", "summary": "This trade is not flagged. The signals restate the stored values.",
                     "signals": [{"type": t, "explanation": "Reported as stored."} for t in types], "limitations": "These indicators do not establish what a member knew."}
    r = generate(desktop, other, manual=True)
    assert r.status_code == 200 and r.json()["ai_context"]["generated_for"] == "manual"
    with session_factory() as s:  # requesting an explanation does not flag the trade
        assert s.scalar(select(TradeContext).where(TradeContext.trade_id == other)).flagged_for_contextual_review is False


def test_unknown_trade_and_missing_context(desktop, flagged):
    save_key(desktop)
    assert generate(desktop, 99999).status_code == 404


def test_offline_generation_fails_cleanly_and_cached_text_stays_readable(desktop, flagged, remote, session_factory):
    save_key(desktop)
    generate(desktop, flagged["big"])
    before = snapshot_context(session_factory)
    remote.raises = httpx.ConnectError("offline", request=httpx.Request("POST", "https://x"))
    r = generate(desktop, flagged["big"], regenerate=True)
    assert r.status_code == 502 and r.json()["detail"]["code"] == "network" and OPENAI_KEY not in r.text
    assert trade_ai(desktop, flagged["big"])["headline"] == GOOD["headline"]  # still readable offline
    assert desktop.get("/api/ai/settings").status_code == 200 and desktop.get("/api/trades").status_code == 200
    assert snapshot_context(session_factory) == before
    remote.raises = httpx.ReadTimeout("slow", request=httpx.Request("POST", "https://x"))
    assert generate(desktop, flagged["big"], regenerate=True).json()["detail"]["code"] == "timeout"


def test_an_invalid_or_revoked_key_is_reported_as_such(desktop, flagged, remote):
    save_key(desktop)
    remote.status = 401
    r = generate(desktop, flagged["big"])
    assert r.status_code == 401 and r.json()["detail"]["code"] == "invalid_key" and OPENAI_KEY not in r.text


def test_two_requests_for_one_trade_cannot_run_at_once(desktop, flagged, remote):
    import poltracker.api.ai as ai_mod

    save_key(desktop)
    ai_mod._in_flight.add(flagged["big"])
    try:
        r = generate(desktop, flagged["big"])
        assert r.status_code == 409 and r.json()["detail"]["code"] == "busy" and remote.requests == []
    finally:
        ai_mod._in_flight.discard(flagged["big"])


# --- bulk ----------------------------------------------------------------------------------------------------------

def test_bulk_previews_only_flagged_trades_and_requires_confirmation(desktop, flagged, remote, session_factory):
    save_key(desktop)
    p = desktop.get("/api/ai/generate-flagged/preview").json()
    with session_factory() as s:
        total = len(list(s.scalars(select(TradeContext))))
    assert total > 1 and p["flagged_total"] == 1 and p["to_generate"] == 1 and p["estimated_api_calls"] == 1 and p["already_cached"] == 0
    assert (p["provider"], p["model"], p["configured"]) == ("openai", "gpt-4o-mini", True)
    assert remote.requests == []  # a preview calls no provider
    assert desktop.post("/api/ai/generate-flagged", json={}).status_code == 400
    assert desktop.post("/api/ai/generate-flagged", json={"confirm": "yes"}).status_code == 400
    assert remote.requests == [] and analyses(session_factory) == []


def test_bulk_generates_only_flagged_trades_respects_the_cache_and_changes_no_flag(desktop, flagged, remote, session_factory):
    save_key(desktop)
    before = snapshot_context(session_factory)
    started = desktop.post("/api/ai/generate-flagged", json={"confirm": True})
    assert started.status_code == 200
    desktop.app_obj.state.ai_bulk.wait()
    st = desktop.get("/api/ai/generate-flagged/status").json()
    assert st["state"] == "done" and st["generated"] == 1 and st["total"] == 1
    assert [a.trade_id for a in analyses(session_factory)] == [flagged["big"]] and len(remote.calls()) == 1
    p = desktop.get("/api/ai/generate-flagged/preview").json()
    assert p["already_cached"] == 1 and p["to_generate"] == 0
    desktop.post("/api/ai/generate-flagged", json={"confirm": True})
    desktop.app_obj.state.ai_bulk.wait()
    assert len(remote.calls()) == 1 and desktop.get("/api/ai/generate-flagged/status").json()["cached"] == 1
    select_provider(desktop, "anthropic")  # another provider has nothing cached yet
    save_key(desktop, "anthropic", CLAUDE_KEY)
    assert desktop.get("/api/ai/generate-flagged/preview").json()["to_generate"] == 1
    assert snapshot_context(session_factory) == before


def test_bulk_without_a_key_does_not_start(desktop, flagged, remote):
    r = desktop.post("/api/ai/generate-flagged", json={"confirm": True})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "not_configured" and remote.requests == []


def test_bulk_stops_on_a_revoked_key_and_reports_it(desktop, flagged, remote):
    save_key(desktop)
    remote.status = 401
    desktop.post("/api/ai/generate-flagged", json={"confirm": True})
    desktop.app_obj.state.ai_bulk.wait()
    st = desktop.get("/api/ai/generate-flagged/status").json()
    assert st["state"] == "failed" and "rejected the API key" in st["message"] and OPENAI_KEY not in json.dumps(st)


# --- public / read-only mode ---------------------------------------------------------------------------------------

def test_the_public_api_has_no_ai_or_keychain_endpoints(session_factory):
    for settings in (Settings(_env_file=None), Settings(_env_file=None, local_views_enabled=True)):
        app = create_app(settings)
        paths = {getattr(r, "path", "") for r in app.routes}
        assert not any("/ai" in p or "ai-context" in p for p in paths)
        c = TestClient(app, base_url="http://127.0.0.1")
        for method, path in (("get", "/ai/settings"), ("post", "/ai/key"), ("delete", "/ai/key"), ("post", "/ai/test"), ("post", "/ai/generate-flagged"),
                             ("put", "/ai/provider"), ("post", "/trades/1/ai-context/generate")):
            assert getattr(c, method)(path).status_code in (404, 405), (method, path)


def test_the_public_api_still_reads_cached_explanations_with_provider_metadata(session_factory, flagged, remote, secrets):
    from poltracker.analyze_trade_context_llm import TradeContextExplanationService
    from poltracker.trade_context_llm import parse_explanation  # noqa: F401

    TradeContextExplanationService(session_factory, remote.factory("anthropic", "k", "claude-haiku-5-5"), model="claude-haiku-5-5", provider="anthropic").run()

    def override():
        with session_factory() as s:
            yield s

    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_session] = override
    ai = TestClient(app).get(f"/trades/{flagged['big']}").json()["context"]["ai_context"]
    assert ai["provider"] == "anthropic" and ai["model"] == "claude-haiku-5-5"
