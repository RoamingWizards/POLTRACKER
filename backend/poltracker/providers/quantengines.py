from .base import CongressProvider, TradePage


class QuantEnginesProvider(CongressProvider):
    """Placeholder. QuantEngines' live dataset was empty (0 trades) when checked on 2026-10-06.

    Verified API: GET {base}/api/v1/trades (skip, limit<=100, ticker, transaction_type,
    politician_id) and /trades/recent/list. Implement once the dataset has data.
    """

    name = "quantengines"

    def fetch_recent_page(self, *, limit: int, offset: int = 0, chamber: str | None = None) -> TradePage:
        raise NotImplementedError("QuantEnginesProvider is not implemented yet")

    def fetch_ticker_page(self, ticker: str, *, limit: int, offset: int = 0) -> TradePage:
        raise NotImplementedError("QuantEnginesProvider is not implemented yet")
