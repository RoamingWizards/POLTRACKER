import re
from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ORIGIN = re.compile(r"^https?://[^/\s?#]+$")


def normalize_database_url(url: str) -> str:
    """Hosting providers hand out `postgres://` / `postgresql://` URLs; SQLAlchemy needs a driver.

    Anything already carrying a driver (`postgresql+psycopg://`) and SQLite URLs pass through untouched.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    # SQLite for local development; set to a PostgreSQL URL in production. Never commit real credentials.
    database_url: str = "sqlite:///./poltracker.db"

    # Comma-separated browser origins allowed to call the API (no trailing slash, no path).
    # Defaults are local dev/preview servers. Production origins come from the CORS_ORIGINS env var.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"

    congressinvests_base_url: str = "https://congressinfor-production.up.railway.app"
    congressinvests_api_key: str | None = None

    # Free tier is 100 requests/day per IP, upstream refreshes every ~6h.
    ingest_page_size: int = 500
    ingest_max_pages: int = Field(15, ge=2)  # >= 2 so a resumed backfill can always move forward
    ingest_interval_hours: float = 6
    # The Data Status page warns when the last successful ingest is older than this.
    ingest_stale_after_hours: float = Field(24, gt=0)

    # Official politician metadata. The key is optional: without it, enrichment reports "not configured" and the
    # rest of the app is unaffected. Get a free key at https://api.congress.gov/sign-up/ and keep it out of git.
    congress_api_key: str | None = None
    congress_api_base_url: str = "https://api.congress.gov/v3"
    congress_number: int = 119  # roster to match against; the current Congress covers trades from the last year
    politician_enrich_stale_days: int = Field(30, ge=1)  # re-enrich matched politicians after this long
    politician_retry_days: int = Field(7, ge=1)  # re-try unmatched/ambiguous politicians after this long
    politician_request_interval: float = Field(0.5, ge=0)  # seconds between official-API requests

    # Optional LLM-assisted identity resolution for politicians the deterministic matcher could not resolve. Off by
    # default; it never runs for resolved politicians and its suggestions are always validated deterministically.
    openai_api_key: str | None = None
    politician_llm_enabled: bool = False
    politician_llm_model: str = "gpt-4o-mini"
    politician_llm_min_confidence: float = Field(0.9, ge=0, le=1)  # a suggestion must meet or exceed this (inclusive)
    politician_llm_max_calls: int = Field(25, ge=0)  # cap per run
    # Off by default: a validated LLM suggestion is held in the review queue and a person approves it (as a reviewed
    # override). Turn on only to let validated suggestions apply directly.
    politician_llm_auto_accept: bool = False

    # OpenAI-written explanations of trade context (python -m poltracker.analyze_trade_context_llm). The model only explains facts the deterministic engine
    # already calculated; it never decides a signal or a flag. Needs OPENAI_API_KEY; without it the explanation is simply unavailable.
    trade_llm_model: str = Field("gpt-4o-mini", validation_alias=AliasChoices("POLTRACKER_TRADE_LLM_MODEL", "trade_llm_model"))
    trade_llm_max_calls: int = Field(25, ge=0, validation_alias=AliasChoices("POLTRACKER_TRADE_LLM_MAX_CALLS", "trade_llm_max_calls"))  # API calls per run
    # Optional USD per million tokens, only for the run summary's cost estimate. Rates change: set them yourself; nothing is assumed.
    trade_llm_input_usd_per_mtok: float | None = Field(None, ge=0, validation_alias=AliasChoices("POLTRACKER_TRADE_LLM_INPUT_USD_PER_MTOK", "trade_llm_input_usd_per_mtok"))
    trade_llm_output_usd_per_mtok: float | None = Field(None, ge=0, validation_alias=AliasChoices("POLTRACKER_TRADE_LLM_OUTPUT_USD_PER_MTOK", "trade_llm_output_usd_per_mtok"))

    # Saved context views and the last-used screen are WRITES to a local table. The desktop app always enables them (single user, same origin); a web API only
    # when you set POLTRACKER_LOCAL_VIEWS=1, because the public API is read-only and has no accounts.
    local_views_enabled: bool = Field(False, validation_alias=AliasChoices("POLTRACKER_LOCAL_VIEWS", "local_views_enabled"))

    # Company profiles (python -m poltracker.enrich_securities) come from SEC EDGAR, whose fair-access policy asks every client to
    # identify itself. Set SEC_USER_AGENT to something like "Your Name your@email.com" (never committed).
    sec_user_agent: str = "POLTRACKER research project (set SEC_USER_AGENT with your contact details)"
    sec_request_interval: float = Field(0.15, ge=0.1)  # seconds between SEC requests (the SEC limit is 10 per second)
    security_profile_stale_days: int = Field(90, ge=1)  # re-check a verified profile after this long
    security_profile_retry_days: int = Field(30, ge=1)  # re-try an unresolved ticker after this long

    benchmark_ticker: str = "SPY"
    price_batch_size: int = 40
    price_retry_days: int = 7  # how long before re-checking a ticker the provider had no data for
    price_tail_overlap_days: int = 7  # refetch overlap, used to detect adjusted-close drift

    @field_validator("database_url")
    @classmethod
    def _normalize_url(cls, value: str) -> str:
        return normalize_database_url(value.strip())

    @field_validator("cors_origins")
    @classmethod
    def _check_origins(cls, value: str) -> str:
        for origin in _split_origins(value):
            if origin != "*" and not _ORIGIN.match(origin):
                raise ValueError(
                    f"CORS_ORIGINS entry {origin!r} must look like https://example.com (scheme and host, no path) or *"
                )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return _split_origins(self.cors_origins)


def _split_origins(value: str) -> list[str]:
    seen: list[str] = []
    for raw in value.split(","):
        origin = raw.strip().rstrip("/")  # a trailing slash is a common mistake and never matches a browser Origin
        if origin and origin not in seen:
            seen.append(origin)
    return seen


@lru_cache
def get_settings() -> Settings:
    return Settings()
