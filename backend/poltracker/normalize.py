"""Pure functions that turn messy provider strings into clean values."""

import hashlib
import re
from datetime import date

from .domain import TradeIn

_HONORIFICS = {"mr", "mrs", "ms", "dr", "hon", "honorable", "sen", "rep", "senator"}
_NO_TICKER = {"", "--", "-", "N/A", "NA", "NONE", "NULL"}


def parse_amount(text: str | None) -> tuple[int | None, int | None]:
    """'$1,001 - $15,000' -> (1001, 15000); 'Over $50,000,000' -> (50000000, None).

    A single figure gives (n, n). Anything unparseable gives (None, None).
    """
    if not text:
        return None, None
    nums = [int(n.replace(",", "")) for n in re.findall(r"\d[\d,]*", text)]
    if not nums:
        return None, None
    if re.search(r"\bover\b|\bmore than\b|\+", text, re.I):
        return nums[0], None
    if len(nums) == 1:
        return nums[0], nums[0]
    return min(nums[:2]), max(nums[:2])


def normalize_name(raw: str) -> str:
    """Drop honorific tokens ('John J Mr McGuire' -> 'John J McGuire') and tidy spacing."""
    tokens = [t for t in raw.replace(",", " ").split() if t.lower().rstrip(".") not in _HONORIFICS]
    return " ".join(tokens)


def politician_key(name: str, chamber: str) -> str:
    return f"{chamber}:{re.sub(r'[^a-z0-9]+', '', name.lower())}"


def normalize_chamber(raw: str | None) -> str | None:
    value = (raw or "").strip().lower()
    return value if value in ("house", "senate") else None


def normalize_ticker(raw: str | None) -> str | None:
    value = (raw or "").strip().upper()
    if value in _NO_TICKER or not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,15}", value):
        return None
    return value


def normalize_transaction_type(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if "partial" in value:
        return "sell_partial"
    if value in ("buy", "purchase", "p"):
        return "buy"
    if value in ("sell", "sale", "s"):
        return "sell"
    if "exchange" in value:
        return "exchange"
    return "unknown"


def clean_asset_name(raw: str | None) -> str | None:
    """Strip filing noise: trailing '[ST]' codes, '(TICK)', and appended type/dates/amount."""
    if not raw:
        return None
    text = raw.strip()
    # Appended junk like ' P 09/08/2026 10/05/2026 $1,001 - $15,000'
    text = re.sub(r"\s+[PSE]\s+\d{2}/\d{2}/\d{4}.*$", "", text)
    text = re.sub(r"\s*\[[A-Z]{1,3}\]", "", text)
    text = re.sub(r"\s*\([A-Z0-9.\-]{1,10}\)", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text or None


def parse_date(raw: str | None) -> date | None:
    try:
        return date.fromisoformat((raw or "").strip()[:10])
    except ValueError:
        return None


def fingerprint(trade: TradeIn, occurrence: int = 0) -> str:
    """Deterministic identity for a trade.

    Provider-neutral on purpose (no source or URL), so the same disclosure from
    another provider or an amended filing maps to the same row. `occurrence`
    separates genuinely identical lines (same member, stock, day, range) that
    appear more than once in a filing.
    """
    parts = [
        politician_key(trade.politician_name, trade.chamber),
        trade.ticker or "",
        trade.asset_name.lower() if trade.asset_name and not trade.ticker else "",
        trade.transaction_type,
        trade.transaction_date.isoformat(),
        trade.disclosure_date.isoformat() if trade.disclosure_date else "",
        str(trade.amount_min),
        str(trade.amount_max),
        str(occurrence),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()
