from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

from ..domain import TradeIn


class ProviderError(Exception):
    pass


class ProviderRateLimited(ProviderError):
    pass


@dataclass
class TradePage:
    trades: list[TradeIn]
    has_more: bool
    total: int | None = None
    skipped: int = 0  # rows the provider returned that could not be normalized


class CongressProvider(ABC):
    """A source of congressional trades. Implementations own all field-name knowledge."""

    name: str

    @abstractmethod
    def fetch_recent_page(self, *, limit: int, offset: int = 0, chamber: str | None = None) -> TradePage:
        """Most recently disclosed trades first."""

    @abstractmethod
    def fetch_ticker_page(self, ticker: str, *, limit: int, offset: int = 0) -> TradePage:
        ...

    def iter_recent_pages(self, *, page_size: int, max_pages: int, start_page: int = 0) -> Iterator[TradePage]:
        """Lazily page through recent trades; the caller stops iterating when caught up."""
        for page_no in range(start_page, start_page + max_pages):
            page = self.fetch_recent_page(limit=page_size, offset=page_no * page_size)
            yield page
            if not page.has_more:
                return
