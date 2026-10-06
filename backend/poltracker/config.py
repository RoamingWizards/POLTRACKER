from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./poltracker.db"

    congressinvests_base_url: str = "https://congressinfor-production.up.railway.app"
    congressinvests_api_key: str | None = None

    # Free tier is 100 requests/day per IP, upstream refreshes every ~6h.
    ingest_page_size: int = 500
    ingest_max_pages: int = 15
    ingest_interval_hours: float = 6

    benchmark_ticker: str = "SPY"
    price_batch_size: int = 40
    price_retry_days: int = 7  # how long before re-checking a ticker the provider had no data for
    price_tail_overlap_days: int = 7  # refetch overlap, used to detect adjusted-close drift


@lru_cache
def get_settings() -> Settings:
    return Settings()
