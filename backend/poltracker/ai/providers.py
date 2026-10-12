"""The AI providers POLTRACKER can use, and the Anthropic implementation. OpenAI's lives in trade_context_llm (it predates the abstraction and is unchanged in behaviour).

Adding a provider: subclass `AIExplanationProvider`, add a `ProviderSpec` to PROVIDERS. Nothing else (storage, API, UI, cache) is provider-specific.
"""

import json
import re
from dataclasses import dataclass

import httpx

from ..trade_context_llm import (
    SCHEMA, SYSTEM, AIExplanationProvider, Explanation, ExplanationError, OpenAIExplanationProvider, build_user_message, http_failure, parse_explanation,
    transport_failure,
)

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models"
ANTHROPIC_VERSION = "2023-06-01"

MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:\-/]{0,79}$")


class AnthropicExplanationProvider(AIExplanationProvider):
    """Claude through the Messages API: no tools, no web search, no streaming. The model is told to answer with one JSON object of the same schema every provider
    uses; the text is parsed strictly (`parse_explanation`) and then goes through the same `validate_explanation` as OpenAI's."""

    provider_name = "anthropic"
    label = "Anthropic (Claude)"

    def __init__(self, api_key: str, model: str, client: httpx.Client | None = None, max_output_tokens: int = 1200):
        if not (api_key or "").strip():
            raise ExplanationError("No Anthropic API key is configured", fatal=True, code="invalid_key")
        self._key, self.model, self._max_output_tokens = api_key.strip(), model, max_output_tokens
        self._client = client or httpx.Client(timeout=60)
        self.requests_made = 0
        self.tokens_in = self.tokens_out = 0

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self._key, "anthropic-version": ANTHROPIC_VERSION}

    def validate_credentials(self) -> None:
        try:
            resp = self._client.get(ANTHROPIC_MODELS_URL, params={"limit": 1}, headers=self._headers())
        except httpx.HTTPError as exc:
            raise transport_failure("Anthropic", exc) from exc
        if resp.status_code != 200:
            raise http_failure("Anthropic", resp.status_code)

    def generate_trade_explanation(self, facts: dict) -> Explanation:
        system = SYSTEM + ("\nAnswer with one JSON object and nothing else (no prose, no code fence) that matches this JSON schema exactly:\n" + json.dumps(SCHEMA))
        body = {"model": self.model, "max_tokens": self._max_output_tokens, "system": system, "messages": [{"role": "user", "content": build_user_message(facts)}]}
        self.requests_made += 1
        try:
            resp = self._client.post(ANTHROPIC_MESSAGES_URL, json=body, headers=self._headers())
        except httpx.HTTPError as exc:
            raise transport_failure("Anthropic", exc) from exc
        if resp.status_code != 200:
            raise http_failure("Anthropic", resp.status_code)  # the body can echo request text; not included
        try:
            data = resp.json()
            usage = data.get("usage") or {}
            self.tokens_in += int(usage.get("input_tokens", 0))
            self.tokens_out += int(usage.get("output_tokens", 0))
            if data.get("type") == "error":
                raise ExplanationError("Anthropic API: the response carried an error")
            stop = data.get("stop_reason")
            blocks = [b for b in data.get("content", []) if isinstance(b, dict)]
        except ExplanationError:
            raise
        except (ValueError, TypeError, AttributeError) as exc:
            raise ExplanationError("Anthropic API: unexpected response shape", code="malformed") from exc
        if stop == "refusal":
            raise ExplanationError("Anthropic API: the model declined to answer", code="refused")
        if stop == "max_tokens":
            raise ExplanationError("Anthropic API: the answer was cut off", code="malformed")
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text" and isinstance(b.get("text"), str)).strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)  # tolerate a code fence even though none was asked for
        try:
            payload = json.loads(text)
        except ValueError as exc:
            raise ExplanationError("Anthropic API: the answer was not valid JSON", code="malformed") from exc
        return parse_explanation(payload)


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    label: str
    cls: type[AIExplanationProvider]
    default_model: str
    suggested_models: tuple[str, ...]
    key_hint: str  # shape of the placeholder only; never a real key


PROVIDERS: dict[str, ProviderSpec] = {
    "openai": ProviderSpec("openai", "OpenAI", OpenAIExplanationProvider, "gpt-4o-mini", ("gpt-4o-mini", "gpt-4o"), "sk-…"),
    "anthropic": ProviderSpec("anthropic", "Anthropic (Claude)", AnthropicExplanationProvider, "claude-haiku-5-5", ("claude-haiku-5-5", "claude-sonnet-5-5"), "sk-ant-…"),
}
DEFAULT_PROVIDER = "openai"


def check_model(model: str) -> str:
    m = (model or "").strip()
    if not MODEL_RE.match(m):
        raise ValueError("A model name is letters, digits and . _ - : / only (up to 80 characters).")
    return m


def build_provider(provider: str, api_key: str, model: str, client: httpx.Client | None = None) -> AIExplanationProvider:
    spec = PROVIDERS[provider]
    return spec.cls(api_key, model, client)
