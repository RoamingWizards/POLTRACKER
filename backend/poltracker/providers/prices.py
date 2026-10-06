"""Market-price provider abstraction. Nothing outside this module imports yfinance."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

log = logging.getLogger(__name__)


class PriceProviderError(Exception):
    pass


@dataclass(frozen=True)
class PriceBarIn:
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None  # split-adjusted, not dividend-adjusted
    adj_close: float | None  # split- and dividend-adjusted; used for returns
    volume: int | None


class PriceProvider(ABC):
    name: str

    @abstractmethod
    def fetch_daily(self, tickers: Sequence[str], start: date, end: date) -> dict[str, list[PriceBarIn]]:
        """Daily bars for the inclusive range [start, end], keyed by the requested ticker.

        Tickers with no data are omitted or empty. Raises PriceProviderError when the
        call as a whole failed (so the caller does not mistake it for 'no data').
        """


def _num(value) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN -> None


class YFinanceProvider(PriceProvider):
    name = "yfinance"

    def __init__(self) -> None:
        # yfinance logs every dead ticker at ERROR; the service reports those itself.
        logging.getLogger("yfinance").setLevel(logging.CRITICAL)

    @staticmethod
    def _to_yahoo(ticker: str) -> str:
        return ticker.replace(".", "-")  # BRK.B -> BRK-B

    def fetch_daily(self, tickers: Sequence[str], start: date, end: date) -> dict[str, list[PriceBarIn]]:
        if not tickers:
            return {}
        import yfinance as yf  # imported here so the rest of the app never needs it

        mapping = {self._to_yahoo(t): t for t in tickers}
        try:
            df = yf.download(
                list(mapping),
                start=start.isoformat(),
                end=(end + timedelta(days=1)).isoformat(),  # yfinance's end is exclusive
                auto_adjust=False,
                group_by="ticker",
                progress=False,
                threads=True,
            )
        except Exception as exc:
            raise PriceProviderError(f"yfinance download failed: {exc}") from exc

        out: dict[str, list[PriceBarIn]] = {}
        if df is None or df.empty:
            return out
        multi = hasattr(df.columns, "levels")
        for yahoo, original in mapping.items():
            if multi:
                if yahoo not in df.columns.get_level_values(0):
                    continue
                sub = df[yahoo]
            else:
                sub = df  # single ticker, flat columns
            sub = sub.dropna(subset=["Close"])
            bars = [
                PriceBarIn(
                    date=idx.date(),
                    open=_num(row.get("Open")),
                    high=_num(row.get("High")),
                    low=_num(row.get("Low")),
                    close=_num(row.get("Close")),
                    adj_close=_num(row.get("Adj Close")),
                    volume=int(row["Volume"]) if _num(row.get("Volume")) is not None else None,
                )
                for idx, row in sub.iterrows()
            ]
            if bars:
                out[original] = bars
        return out
