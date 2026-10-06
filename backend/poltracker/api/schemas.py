from datetime import date

from pydantic import BaseModel, ConfigDict


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
    trade_count: int
    latest_trade_date: date | None
    recent_trades: list[TradeOut]
