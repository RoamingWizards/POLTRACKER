"""Company profile providers: official identifiers and industry classification for a ticker.

The default provider is SEC EDGAR: ticker -> CIK from the SEC's published ticker list, then the company's SIC code and description
from its EDGAR submissions record. Everything is looked up, never inferred, and nothing here involves a language model. A ticker the
source does not list stays unresolved; there is no fuzzy name matching.
"""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass

import httpx

from .base import ProviderError, ProviderRateLimited

log = logging.getLogger(__name__)

SOURCE = "sec-edgar"
TICKER_LIST_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
TICKER_TXT_URL = "https://www.sec.gov/include/ticker.txt"  # older official list; covers some tickers the JSON list omits
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
BROWSE_URL = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}"

# Official SIC divisions (the SEC and OSHA publish this grouping of SIC major groups, the first two digits of the SIC code).
_DIVISIONS = [
    (1, 9, "Agriculture, Forestry, and Fishing"),
    (10, 14, "Mining"),
    (15, 17, "Construction"),
    (20, 39, "Manufacturing"),
    (40, 49, "Transportation, Communications, Electric, Gas, and Sanitary Services"),
    (50, 51, "Wholesale Trade"),
    (52, 59, "Retail Trade"),
    (60, 67, "Finance, Insurance, and Real Estate"),
    (70, 89, "Services"),
    (91, 99, "Public Administration"),
]


def sic_division(sic: str | None) -> str | None:
    """The official SIC division for a 4-digit SIC code, or None when the code is missing or outside the published groups."""
    if not sic or not sic.isdigit() or len(sic) != 4:
        return None
    major = int(sic[:2])
    return next((name for lo, hi, name in _DIVISIONS if lo <= major <= hi), None)


@dataclass(frozen=True)
class CompanyProfile:
    ticker: str
    company_name: str | None
    cik: str  # zero-padded to 10 digits
    sic_code: str | None = None
    industry: str | None = None  # the official SIC description
    sector: str | None = None  # the official SIC division
    exchange: str | None = None
    source: str = SOURCE
    source_url: str | None = None


class CompanyProfileProvider(ABC):
    name: str

    @abstractmethod
    def prepare(self, tickers: Iterable[str]) -> None:
        """Bulk lookups done once per run (raises ProviderError if the source is unreachable)."""

    @abstractmethod
    def get_profile(self, ticker: str) -> CompanyProfile | None:
        """The profile for a ticker, or None when the source does not list it."""


def ticker_variants(ticker: str) -> list[str]:
    """The ticker as given, then the one deterministic alternative: SEC writes class shares with a hyphen (BRK-B), others with a dot."""
    t = ticker.strip().upper()
    out = [t]
    for a, b in ((".", "-"), ("-", ".")):
        if a in t and t.replace(a, b) not in out:
            out.append(t.replace(a, b))
    return out


class SecEdgarProvider(CompanyProfileProvider):
    name = SOURCE

    def __init__(
        self,
        user_agent: str,
        *,
        client: httpx.Client | None = None,
        min_interval: float = 0.15,  # SEC allows at most 10 requests per second
        max_retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._client = client or httpx.Client(timeout=40, headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
        self._min_interval, self._max_retries, self._sleep, self._clock = min_interval, max_retries, sleep, clock
        self._last = None
        self._tickers: dict[str, list[tuple[int, str | None, str | None]]] | None = None
        self.requests_made = 0

    def _get(self, url: str) -> dict:
        for attempt in range(self._max_retries + 1):
            if self._last is not None:
                wait = self._min_interval - (self._clock() - self._last)
                if wait > 0:
                    self._sleep(wait)
            self._last = self._clock()
            self.requests_made += 1
            try:
                resp = self._client.get(url)
            except httpx.HTTPError as exc:
                error: ProviderError = ProviderError(f"{_host(url)}: network error ({type(exc).__name__})")
            else:
                if resp.status_code == 404:
                    raise ProviderError(f"{_host(url)}: not found (HTTP 404)")
                if resp.status_code in (403, 429):  # SEC answers a rate-limit breach with 403/429 and a block page
                    error = ProviderRateLimited(f"{_host(url)}: rate limited or refused (HTTP {resp.status_code}); SEC_USER_AGENT may need real contact details")
                elif resp.status_code >= 500:
                    error = ProviderError(f"{_host(url)}: server error (HTTP {resp.status_code})")
                elif resp.status_code >= 400:
                    raise ProviderError(f"{_host(url)}: HTTP {resp.status_code}")
                else:
                    try:
                        body = resp.json()
                    except ValueError as exc:
                        raise ProviderError(f"{_host(url)}: response was not JSON") from exc
                    if not isinstance(body, dict):
                        raise ProviderError(f"{_host(url)}: unexpected response shape")
                    return body
            if attempt == self._max_retries:
                raise error
            self._sleep(min(2 ** (attempt + 1), 30))
        raise AssertionError("unreachable")

    def _get_text(self, url: str) -> str:
        """Same pacing, retry and error handling as _get, for the plain-text ticker list."""
        for attempt in range(self._max_retries + 1):
            if self._last is not None:
                wait = self._min_interval - (self._clock() - self._last)
                if wait > 0:
                    self._sleep(wait)
            self._last = self._clock()
            self.requests_made += 1
            try:
                resp = self._client.get(url)
            except httpx.HTTPError as exc:
                error: ProviderError = ProviderError(f"{_host(url)}: network error ({type(exc).__name__})")
            else:
                if resp.status_code in (403, 429):
                    error = ProviderRateLimited(f"{_host(url)}: rate limited or refused (HTTP {resp.status_code})")
                elif resp.status_code >= 500:
                    error = ProviderError(f"{_host(url)}: server error (HTTP {resp.status_code})")
                elif resp.status_code >= 400:
                    raise ProviderError(f"{_host(url)}: HTTP {resp.status_code}")
                else:
                    return resp.text
            if attempt == self._max_retries:
                raise error
            self._sleep(min(2 ** (attempt + 1), 30))
        raise AssertionError("unreachable")

    def _load_txt_list(self) -> None:
        """Optional fallback list: 'ticker<TAB>cik' lines. A failure here only reduces coverage; rate limiting still stops the run."""
        self._txt: dict[str, set[int]] = {}
        try:
            text = self._get_text(TICKER_TXT_URL)
        except ProviderRateLimited:
            raise
        except ProviderError as exc:
            log.warning("SEC fallback ticker list unavailable (%s); continuing with the primary list only", exc)
            return
        for line in text.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                self._txt.setdefault(parts[0].strip().upper(), set()).add(int(parts[1]))

    def prepare(self, tickers: Iterable[str]) -> None:
        body = self._get(TICKER_LIST_URL)
        fields, rows = body.get("fields"), body.get("data")
        if not isinstance(fields, list) or not isinstance(rows, list) or not {"cik", "ticker"} <= set(fields):
            raise ProviderError("SEC ticker list: unexpected shape")
        ix = {name: i for i, name in enumerate(fields)}
        by_ticker: dict[str, list] = {}
        for row in rows:
            try:
                cik, ticker = int(row[ix["cik"]]), str(row[ix["ticker"]]).strip().upper()
            except (TypeError, ValueError, IndexError):
                continue
            if ticker:
                name = row[ix["name"]] if "name" in ix else None
                exchange = row[ix["exchange"]] if "exchange" in ix else None
                by_ticker.setdefault(ticker, []).append((cik, name if isinstance(name, str) else None, exchange if isinstance(exchange, str) else None))
        self._tickers = by_ticker
        self._load_txt_list()

    def get_profile(self, ticker: str) -> CompanyProfile | None:
        if self._tickers is None:
            self.prepare([ticker])
        for variant in ticker_variants(ticker):
            found = self._tickers.get(variant)
            if not found:
                # Fallback: the older official ticker.txt list, exact ticker only (so still no name matching).
                ciks = getattr(self, "_txt", {}).get(variant)
                if not ciks:
                    continue
                found = [(next(iter(ciks)), None, None)] if len(ciks) == 1 else [(c, None, None) for c in sorted(ciks)]
            if len({c for c, _n, _e in found}) > 1:  # one ticker listed under several CIKs: never pick one
                return None
            cik, list_name, exchange = found[0]
            padded = f"{cik:010d}"
            body = self._get(SUBMISSIONS_URL.format(cik=padded))
            sic = str(body.get("sic") or "").strip()
            sic = sic.zfill(4) if sic.isdigit() and int(sic) > 0 else None
            exchanges = [e for e in body.get("exchanges") or [] if isinstance(e, str) and e.strip()]
            return CompanyProfile(
                ticker=ticker.strip().upper(),
                company_name=(body.get("name") or list_name or "").strip() or None,
                cik=padded,
                sic_code=sic,
                industry=(body.get("sicDescription") or "").strip() or None if sic else None,
                sector=sic_division(sic),
                exchange=exchange or (exchanges[0] if exchanges else None),
                source_url=BROWSE_URL.format(cik=padded),
            )
        return None

    def is_ambiguous(self, ticker: str) -> bool:
        return any(len({c for c, _n, _e in self._tickers.get(v, [])}) > 1 for v in ticker_variants(ticker)) if self._tickers else False


def _host(url: str) -> str:
    return url.split("/")[2] if "//" in url else url
