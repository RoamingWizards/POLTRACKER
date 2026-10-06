import logging
from typing import Any

import httpx

from ..domain import TradeIn
from ..normalize import (
    clean_asset_name,
    normalize_chamber,
    normalize_name,
    normalize_ticker,
    normalize_transaction_type,
    parse_amount,
    parse_date,
)
from .base import CongressProvider, ProviderError, ProviderRateLimited, TradePage

log = logging.getLogger(__name__)

SOURCE = "congressinvests"


def normalize_record(rec: dict[str, Any]) -> TradeIn | None:
    """Map one CongressInvests trade object to TradeIn. None if it can't be used."""
    chamber = normalize_chamber(rec.get("chamber"))
    name = normalize_name(rec.get("member") or "")
    tx_date = parse_date(rec.get("tx_date"))
    if not (chamber and name and tx_date):
        return None
    amount_min, amount_max = parse_amount(rec.get("amount"))
    return TradeIn(
        source=SOURCE,
        politician_name=name,
        chamber=chamber,
        transaction_type=normalize_transaction_type(rec.get("trade_type")),
        transaction_date=tx_date,
        ticker=normalize_ticker(rec.get("ticker")),
        asset_name=clean_asset_name(rec.get("asset")),
        disclosure_date=parse_date(rec.get("disclosed")),
        amount_min=amount_min,
        amount_max=amount_max,
        source_url=rec.get("link") or None,
    )


class CongressInvestsProvider(CongressProvider):
    name = SOURCE

    def __init__(self, base_url: str, api_key: str | None = None, client: httpx.Client | None = None):
        headers = {"Accept": "application/json"}
        if api_key:
            headers["X-Api-Key"] = api_key
        self._client = client or httpx.Client(base_url=base_url.rstrip("/"), headers=headers, timeout=30)
        self.requests_made = 0

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        self.requests_made += 1
        try:
            resp = self._client.get(path, params={k: v for k, v in params.items() if v is not None})
        except httpx.HTTPError as exc:
            raise ProviderError(f"{path}: {exc}") from exc
        if resp.status_code == 429:
            raise ProviderRateLimited(f"{path}: daily request limit reached")
        if resp.status_code >= 400:
            raise ProviderError(f"{path}: HTTP {resp.status_code}")
        try:
            return resp.json()
        except ValueError as exc:
            raise ProviderError(f"{path}: response was not JSON") from exc

    @staticmethod
    def _to_page(body: dict[str, Any]) -> TradePage:
        trades, skipped = [], 0
        for rec in body.get("trades", []):
            trade = normalize_record(rec)
            if trade is None:
                skipped += 1
                log.warning("Skipping unusable record: %s", rec)
            else:
                trades.append(trade)
        return TradePage(trades=trades, has_more=bool(body.get("has_more")), total=body.get("total"), skipped=skipped)

    def fetch_recent_page(self, *, limit: int, offset: int = 0, chamber: str | None = None) -> TradePage:
        return self._to_page(self._get("/trades/recent", {"limit": limit, "offset": offset, "chamber": chamber}))

    def fetch_ticker_page(self, ticker: str, *, limit: int, offset: int = 0) -> TradePage:
        return self._to_page(self._get(f"/trades/{ticker.upper()}", {"limit": limit, "offset": offset, "format": "json"}))
