"""In-app AI provider configuration and on-demand explanations. These routes WRITE and reach the keychain, so they are mounted only in the desktop app (same origin, single
user) and never on the public read-only API.

Rules this module keeps:
- an API key is accepted by POST /ai/key, written to the keychain and forgotten; no response, log line or error message contains it (the request body is parsed by hand
  so a validation error can never echo it back);
- the AI explains, it never decides: nothing here writes `trade_context`, and requesting an explanation never changes a flag;
- nothing calls a provider unless the user asked: opening a dialog or the settings page only reads.
"""

import contextlib
import threading
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.bulk import BulkJob
from ..ai.keystore import SecretStore, SecretStoreError, clean_key, mask_key
from ..ai.providers import DEFAULT_PROVIDER, PROVIDERS, build_provider, check_model
from ..ai.settings import AiSettings, load_settings, save_settings
from ..analyze_trade_context_llm import ItemResult, TradeContextExplanationService
from ..models import TradeContext
from ..trade_context_llm import PROMPT_VERSION, ExplanationError
from .main import _context_key, get_session
from .schemas import AiContextOut, AiSignalExplanationOut

router = APIRouter()

NOT_ELIGIBLE = "Only trades flagged by the default POLTRACKER methodology are explained by default."
REJECTED_MESSAGE = "AI explanation could not be generated from the available evidence."
MALFORMED_MESSAGE = "The AI provider returned an answer in an unexpected format. Nothing was saved."
LOOPBACK = {"127.0.0.1", "localhost", "[::1]"}


# --- guards ----------------------------------------------------------------------------------------------------------

def local_write(request: Request) -> None:
    """A browser page on another site must not be able to save a key or spend the user's quota: writes need a JSON content type (which forces a CORS preflight that this
    server never grants) and, when the browser names an origin, that origin must be this machine."""
    origin = request.headers.get("origin")
    if origin and origin != "null" and (urlsplit(origin).hostname or "") not in {h.strip("[]") for h in LOOPBACK}:
        raise HTTPException(403, "Requests from other sites are not allowed.")
    if request.method in ("POST", "PUT") and not request.headers.get("content-type", "").lower().startswith("application/json"):
        raise HTTPException(415, "Send application/json.")


def secrets_of(request: Request) -> SecretStore:
    return request.app.state.ai_secrets


def _factory(request: Request):
    return request.app.state.ai_provider_factory


def _bulk(request: Request) -> BulkJob:
    return request.app.state.ai_bulk


def _fail(status: int, code: str, message: str):
    raise HTTPException(status, {"code": code, "message": message})


async def _json_body(request: Request) -> dict:
    try:
        data = await request.json()
    except ValueError:
        _fail(400, "bad_request", "The request body was not valid JSON.")
    if not isinstance(data, dict):
        _fail(400, "bad_request", "The request body must be a JSON object.")
    return data


def _provider_id(value: object) -> str:
    if not isinstance(value, str) or value not in PROVIDERS:
        _fail(400, "unknown_provider", "Unknown AI provider.")
    return value


# --- settings --------------------------------------------------------------------------------------------------------

class ProviderStateOut(BaseModel):
    id: str
    label: str
    configured: bool
    masked: str | None = None  # 'sk-••••••••1234'. The stored key itself is never returned.
    model: str
    default_model: str
    suggested_models: list[str]


class AiSettingsOut(BaseModel):
    provider: str
    model: str
    providers: list[ProviderStateOut]
    configured: bool  # the selected provider has a key
    storage_error: str | None = None
    notice: str = "AI does not determine which trades POLTRACKER flags. It explains the deterministic context already calculated by POLTRACKER."
    key_notice: str = "Your API key is stored locally in the macOS Keychain and is sent only to the selected AI provider when you request an explanation."


def _settings_out(request: Request, session: Session) -> AiSettingsOut:
    cfg = load_settings(session)
    store, error, states = secrets_of(request), None, []
    for pid, spec in PROVIDERS.items():
        key = None
        try:
            key = store.get(pid)
        except SecretStoreError as exc:
            error = str(exc)
        states.append(ProviderStateOut(id=pid, label=spec.label, configured=bool(key), masked=mask_key(key) if key else None, model=cfg.model_for(pid),
                                       default_model=spec.default_model, suggested_models=list(spec.suggested_models)))
    return AiSettingsOut(provider=cfg.provider, model=cfg.model_for(), providers=states, configured=any(p.id == cfg.provider and p.configured for p in states), storage_error=error)


@router.get("/ai/settings", response_model=AiSettingsOut)
def get_ai_settings(request: Request, session: Session = Depends(get_session)) -> AiSettingsOut:
    return _settings_out(request, session)


@router.put("/ai/provider", response_model=AiSettingsOut, dependencies=[Depends(local_write)])
async def put_ai_provider(request: Request, session: Session = Depends(get_session)) -> AiSettingsOut:
    body = await _json_body(request)
    provider = _provider_id(body.get("provider"))
    cfg = load_settings(session)
    cfg.provider = provider
    if "model" in body:
        raw = body["model"]
        if raw in (None, ""):
            cfg.models.pop(provider, None)  # back to the provider's default
        else:
            try:
                cfg.models[provider] = check_model(raw if isinstance(raw, str) else "")
            except ValueError as exc:
                _fail(400, "bad_model", str(exc))
    save_settings(session, cfg)
    return _settings_out(request, session)


@router.post("/ai/key", response_model=AiSettingsOut, dependencies=[Depends(local_write)])
async def save_ai_key(request: Request, session: Session = Depends(get_session)) -> AiSettingsOut:
    body = await _json_body(request)
    provider = _provider_id(body.get("provider"))
    try:
        key = clean_key(body.get("api_key"))
    except ValueError as exc:
        _fail(400, "bad_key", str(exc))
    try:
        secrets_of(request).set(provider, key)
    except SecretStoreError as exc:
        _fail(503, "keychain_unavailable", str(exc))
    return _settings_out(request, session)


@router.delete("/ai/key", response_model=AiSettingsOut, dependencies=[Depends(local_write)])
def delete_ai_key(request: Request, provider: str, session: Session = Depends(get_session)) -> AiSettingsOut:
    pid = _provider_id(provider)
    try:
        secrets_of(request).delete(pid)
    except SecretStoreError as exc:
        _fail(503, "keychain_unavailable", str(exc))
    return _settings_out(request, session)


class TestResult(BaseModel):
    ok: bool
    code: str | None = None
    message: str


@router.post("/ai/test", response_model=TestResult, dependencies=[Depends(local_write)])
async def test_ai_connection(request: Request, session: Session = Depends(get_session)) -> TestResult:
    """Checks the saved key with a request that spends no tokens (the provider's model list). Always 200: the result says whether it worked."""
    body = await _json_body(request)
    cfg = load_settings(session)
    provider = _provider_id(body.get("provider", cfg.provider))
    try:
        key = secrets_of(request).get(provider)
    except SecretStoreError as exc:
        return TestResult(ok=False, code="keychain_unavailable", message=str(exc))
    if not key:
        return TestResult(ok=False, code="not_configured", message=f"No {PROVIDERS[provider].label} API key is saved.")
    try:
        _factory(request)(provider, key, cfg.model_for(provider)).validate_credentials()
    except ExplanationError as exc:
        return TestResult(ok=False, code=exc.code, message=str(exc))
    return TestResult(ok=True, message=f"Connected to {PROVIDERS[provider].label}.")


# --- one trade -------------------------------------------------------------------------------------------------------

_in_flight: set[int] = set()
_in_flight_lock = threading.Lock()


class GenerateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regenerate: bool = False  # ask the provider again even though a valid cached explanation exists
    manual: bool = False  # explicit advanced action: explain a trade that is NOT flagged by the default methodology


class GenerateOut(BaseModel):
    ai_context: AiContextOut
    from_cache: bool


def _ai_out_from(item: ItemResult) -> AiContextOut:
    e = item.explanation or {}
    return AiContextOut(headline=e["headline"], summary=e["summary"], signals=[AiSignalExplanationOut(**s) for s in e["signals"]], limitations=e["limitations"],
                        generated_for=e["generated_for"], provider=e["provider"], model=e["model"], prompt_version=PROMPT_VERSION, generated_at=e["generated_at"])


def _usable_provider(request: Request, session: Session):
    """(settings, provider id, key). Raises 409 not_configured when the chosen provider has no key."""
    cfg = load_settings(session)
    try:
        key = secrets_of(request).get(cfg.provider)
    except SecretStoreError as exc:
        _fail(503, "keychain_unavailable", str(exc))
    if not key:
        _fail(409, "not_configured", f"No {PROVIDERS[cfg.provider].label} API key is saved. Configure an AI provider first.")
    return cfg, key


_STATUS = {"invalid_key": 401, "rate_limited": 429, "unavailable": 503, "network": 502, "timeout": 504, "refused": 502}


@router.post("/trades/{trade_id}/ai-context/generate", response_model=GenerateOut, dependencies=[Depends(local_write)])
def generate_for_trade(trade_id: int, body: GenerateIn, request: Request, session: Session = Depends(get_session)) -> GenerateOut:
    key_ = _context_key(session)
    ctx = session.scalar(select(TradeContext).where(TradeContext.trade_id == trade_id, TradeContext.context_version == key_[0], TradeContext.mapping_version == key_[1])) if key_ else None
    if ctx is None:
        _fail(404, "no_context", "Context has not been calculated for this trade.")
    if not ctx.flagged_for_contextual_review and not body.manual:
        _fail(409, "not_flagged", NOT_ELIGIBLE)
    cfg, api_key = _usable_provider(request, session)
    if _bulk(request).running:
        _fail(409, "busy", "A bulk generation is running. Wait for it to finish.")
    with _in_flight_lock:
        if trade_id in _in_flight:
            _fail(409, "busy", "An explanation for this trade is already being generated.")
        _in_flight.add(trade_id)
    try:
        model = cfg.model_for()
        provider = _factory(request)(cfg.provider, api_key, model)
        service = TradeContextExplanationService(lambda: contextlib.nullcontext(session), provider, model=model, provider=cfg.provider, max_calls=1)
        summary = service.run(trade_ids=[trade_id], flagged_only=False, force=body.regenerate, limit=1)
    except ExplanationError as exc:
        _fail(_STATUS.get(exc.code, 502), exc.code, str(exc))
    finally:
        with _in_flight_lock:
            _in_flight.discard(trade_id)
    if not summary.items:
        _fail(404, "no_context", "Context has not been calculated for this trade.")
    item = summary.items[0]
    if item.status in ("generated", "cached"):
        return GenerateOut(ai_context=_ai_out_from(item), from_cache=item.status == "cached")
    if item.status == "rejected":
        _fail(422, "validation_rejected", REJECTED_MESSAGE)  # the rejected text is never returned
    code = item.code or "error"
    _fail(_STATUS.get(code, 502), code, MALFORMED_MESSAGE if code == "malformed" else (item.reasons[0] if item.reasons else "The explanation could not be generated."))


# --- every flagged trade ---------------------------------------------------------------------------------------------

class BulkPreviewOut(BaseModel):
    provider: str
    provider_label: str
    model: str
    configured: bool
    flagged_total: int
    already_cached: int
    to_generate: int
    estimated_api_calls: int


def _flagged_service(request: Request, session_factory, provider=None, cfg: AiSettings | None = None):
    cfg = cfg or AiSettings()
    return TradeContextExplanationService(session_factory, provider, model=cfg.model_for(), provider=cfg.provider, max_calls=10**6)


@router.get("/ai/generate-flagged/preview", response_model=BulkPreviewOut)
def preview_bulk(request: Request, session: Session = Depends(get_session)) -> BulkPreviewOut:
    """What a bulk run would do, without calling any provider: flagged trades only, cache respected."""
    cfg = load_settings(session)
    try:
        configured = bool(secrets_of(request).get(cfg.provider))
    except SecretStoreError:
        configured = False
    summary = _flagged_service(request, lambda: contextlib.nullcontext(session), None, cfg).run(flagged_only=True, dry_run=True)
    return BulkPreviewOut(provider=cfg.provider, provider_label=PROVIDERS[cfg.provider].label, model=cfg.model_for(), configured=configured, flagged_total=summary.selected,
                          already_cached=summary.cached, to_generate=summary.would_generate, estimated_api_calls=summary.would_generate)


@router.post("/ai/generate-flagged", dependencies=[Depends(local_write)])
async def start_bulk(request: Request, session: Session = Depends(get_session)) -> dict:
    body = await _json_body(request)
    if body.get("confirm") is not True:
        _fail(400, "confirmation_required", "Confirm the bulk generation to start it.")
    cfg, api_key = _usable_provider(request, session)
    job = _bulk(request)
    if _in_flight:
        _fail(409, "busy", "An explanation is being generated. Try again in a moment.")
    factory = request.app.state.ai_session_factory
    model = cfg.model_for()
    preview = _flagged_service(request, lambda: contextlib.nullcontext(session), None, cfg).run(flagged_only=True, dry_run=True)
    todo = preview.would_generate

    def work(update):
        provider = _factory(request)(cfg.provider, api_key, model)
        service = TradeContextExplanationService(factory, provider, model=model, provider=cfg.provider, max_calls=max(todo, 0))
        return service.run(flagged_only=True, on_item=lambda _item, summary: update(summary))

    if not job.start(work, provider=cfg.provider, model=model, total=preview.selected):
        _fail(409, "busy", "A bulk generation is already running.")
    return job.snapshot()


@router.get("/ai/generate-flagged/status")
def bulk_status(request: Request) -> dict:
    return _bulk(request).snapshot()
