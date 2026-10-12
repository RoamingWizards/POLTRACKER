"""Which provider and model the user chose. These are preferences, not secrets: they live in app_preferences. API keys never do (see keystore)."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from ..models import AppPreference
from .providers import DEFAULT_PROVIDER, PROVIDERS

KEY = "ai_settings"


@dataclass
class AiSettings:
    provider: str = DEFAULT_PROVIDER
    models: dict[str, str] = field(default_factory=dict)  # provider id -> chosen model; absent means the provider's default

    def model_for(self, provider: str | None = None) -> str:
        p = provider or self.provider
        return self.models.get(p) or PROVIDERS[p].default_model


def load_settings(session: Session) -> AiSettings:
    try:
        with session.begin_nested():
            row = session.get(AppPreference, KEY)
    except (OperationalError, ProgrammingError):
        return AiSettings()
    if row is None:
        return AiSettings()
    try:
        data = json.loads(row.value_json)
        provider = data.get("provider")
        models = {p: m for p, m in (data.get("models") or {}).items() if p in PROVIDERS and isinstance(m, str) and m}
        return AiSettings(provider if provider in PROVIDERS else DEFAULT_PROVIDER, models)
    except (ValueError, AttributeError):
        return AiSettings()


def save_settings(session: Session, settings: AiSettings) -> None:
    payload = json.dumps({"provider": settings.provider, "models": settings.models})
    now = datetime.now(UTC).replace(tzinfo=None)
    row = session.get(AppPreference, KEY)
    if row is None:
        session.add(AppPreference(key=KEY, value_json=payload, updated_at=now))
    else:
        row.value_json, row.updated_at = payload, now
    session.commit()
