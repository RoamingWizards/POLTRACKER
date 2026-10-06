from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    politician_id: int
    security_id: int | None
    politician_name: str
    chamber: str
    party: str | None
    state: str | None
    ticker: str | None
    asset_name: str | None
    transaction_type: str
    transaction_date: date
    disclosure_date: date | None
    amount_min: int | None
    amount_max: int | None
    source_url: str | None


class TradePageOut(BaseModel):
    items: list[TradeOut]
    total: int
    limit: int
    offset: int


class PoliticianOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    chamber: str
    party: str | None
    state: str | None
    trade_count: int = 0
    latest_trade_date: date | None = None


class PoliticianPageOut(BaseModel):
    items: list[PoliticianOut]
    total: int
    limit: int
    offset: int


class SecurityOut(BaseModel):
    id: int
    ticker: str
    name: str | None
    price_status: str | None = None
    price_from: date | None = None
    price_to: date | None = None
    trade_count: int
    latest_trade_date: date | None
    recent_trades: list[TradeOut]


class PriceBarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    adj_close: float | None
    volume: int | None


class PriceSeriesOut(BaseModel):
    ticker: str
    price_status: str | None
    price_from: date | None
    price_to: date | None
    bars: list[PriceBarOut]


class LegOut(BaseModel):
    status: str
    anchor_date: date | None = None
    price: float | None = None
    return_: float | None = Field(None, serialization_alias="return", validation_alias="return_")
    benchmark_return: float | None = None
    excess_return: float | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PerformanceOut(BaseModel):
    """Returns are fractions of adjusted close (0.10 = +10%). `direction_adjusted` flips sign for sells."""

    status: str
    detail: str | None = None
    benchmark: str | None = None
    latest_date: date | None = None
    latest_price: float | None = None
    direction: int | None = None
    transaction: LegOut | None = None
    disclosure: LegOut | None = None
    direction_adjusted: dict[str, float | None] = {}

    model_config = ConfigDict(from_attributes=True)


class TradePerformanceOut(BaseModel):
    trade: TradeOut
    performance: PerformanceOut


class SecurityPerformanceOut(BaseModel):
    ticker: str
    benchmark: str
    status_counts: dict[str, int]
    total: int
    items: list[TradePerformanceOut]


class DailyCount(BaseModel):
    date: date
    count: int


class MonthlyCount(BaseModel):
    month: str  # YYYY-MM, by disclosure date
    buys: int
    sells: int
    other: int


class TopTicker(BaseModel):
    ticker: str
    name: str | None
    trades: int
    buys: int
    sells: int


class TopPolitician(BaseModel):
    id: int
    name: str
    chamber: str
    trades: int


class OverviewTotals(BaseModel):
    trades: int
    politicians: int
    securities: int
    trades_in_window: int
    buys_in_window: int
    sells_in_window: int


class OverviewOut(BaseModel):
    window_days: int
    totals: OverviewTotals
    latest_disclosure_date: date | None
    daily: list[DailyCount]
    monthly: list[MonthlyCount]
    top_tickers: list[TopTicker]
    top_politicians: list[TopPolitician]


class StatusOut(BaseModel):
    trades_total: int
    trades_by_source: dict[str, int]
    politicians_total: int
    latest_disclosure_date: date | None
    latest_transaction_date: date | None
    last_ingested_at: datetime | None  # when the newest trade row was inserted
    last_successful_ingest_at: datetime | None  # when the last ingest run finished without error
    ingest_age_hours: float | None
    ingest_stale_after_hours: float
    ingest_stale: bool
    invalid_date_trades: int
    securities_total: int
    securities_priced: int
    securities_unavailable: int
    securities_pending: int
    price_bars: int
    latest_bar_date: date | None
    benchmark_ticker: str
    benchmark_from: date | None
    benchmark_to: date | None
    benchmark_status: str | None
