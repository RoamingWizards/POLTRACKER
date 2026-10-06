"""Provider-neutral trade shape. Providers map their payloads into TradeIn."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TradeIn:
    source: str
    politician_name: str
    chamber: str  # "house" | "senate"
    transaction_type: str  # "buy" | "sell" | "sell_partial" | "exchange" | "unknown"
    transaction_date: date
    source_trade_id: str | None = None
    party: str | None = None
    state: str | None = None
    ticker: str | None = None
    asset_name: str | None = None
    disclosure_date: date | None = None
    amount_min: int | None = None
    amount_max: int | None = None
    source_url: str | None = None
