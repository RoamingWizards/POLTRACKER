"""
US Politician Stock Trade Tracker
----------------------------------
Pulls House representative trades from House Stock Watcher (free, no key needed)
Enriches with price performance data from Finnhub (free API key required)
Sends a daily Telegram digest of notable trades

Setup:
1. pip3 install requests schedule
2. Get a free Finnhub key at finnhub.io (takes 2 minutes)
3. Fill in your keys below
4. Run: python3 politician_tracker.py
"""

import requests
import schedule
import time
import json
import logging
from datetime import datetime, timedelta

# ── CONFIG ────────────────────────────────────────────────────────────────────

FINNHUB_API_KEY  = "d78il0pr01qp0fl5c6jgd78il0pr01qp0fl5c6k0"    # finnhub.io — free tier
TELEGRAM_TOKEN   = "8630626977:AAGE1U2SithGfQqRQxJdx_w9IjOMbZ-O_nw"
TELEGRAM_CHAT_ID = "845938381"

# Filtering
MIN_TRADE_VALUE      = 15000    # ignore trades below this ($ estimated value)
MIN_PRICE_MOVE_PCT   = 5.0      # flag if stock moved more than this % since trade
TOP_N_TRADES         = 10       # how many trades to show in daily digest
LOOKBACK_DAYS        = 30       # how many days of trades to pull

# Schedule — sends digest once a day at this time
DIGEST_TIME          = "08:00"  # 24hr format

# ── LOGGING ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── TELEGRAM ──────────────────────────────────────────────────────────────────

def send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # Telegram has a 4096 char limit — split if needed
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": "HTML"}
        try:
            r = requests.post(url, json=payload, timeout=10)
            r.raise_for_status()
        except Exception as e:
            log.error(f"Telegram error: {e}")

# ── HOUSE STOCK WATCHER ───────────────────────────────────────────────────────

def fetch_trades() -> list:
    """
    Fetch all House representative trades from House Stock Watcher.
    Returns trades from the last LOOKBACK_DAYS days only.
    No API key required.
    """
    url = "https://house-stock-watcher-data.s3-us-east-2.amazonaws.com/data/all_transactions.json"
    try:
        log.info("Fetching trades from House Stock Watcher...")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        all_trades = r.json()
        log.info(f"Fetched {len(all_trades)} total trades")

        # Filter to recent trades only
        cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
        recent = []
        for trade in all_trades:
            try:
                trade_date = datetime.strptime(trade["transaction_date"], "%Y-%m-%d")
                if trade_date >= cutoff:
                    recent.append(trade)
            except (ValueError, KeyError):
                continue

        log.info(f"{len(recent)} trades in last {LOOKBACK_DAYS} days")
        return recent

    except Exception as e:
        log.error(f"Failed to fetch trades: {e}")
        return []


def parse_trade_value(amount_str: str) -> int:
    """
    Convert amount range string to midpoint integer.
    e.g. "$15,001 - $50,000" → 32500
    """
    ranges = {
        "$1,001 - $15,000":     8000,
        "$15,001 - $50,000":    32500,
        "$50,001 - $100,000":   75000,
        "$100,001 - $250,000":  175000,
        "$250,001 - $500,000":  375000,
        "$500,001 - $1,000,000":750000,
        "Over $1,000,000":      1500000,
    }
    for key, val in ranges.items():
        if key.lower() in amount_str.lower():
            return val
    return 0

# ── FINNHUB PRICE DATA ────────────────────────────────────────────────────────

def get_price_on_date(ticker: str, date_str: str) -> float | None:
    """Get closing price for a ticker on a specific date using Finnhub."""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        # Use next trading day if weekend
        while date.weekday() >= 5:
            date += timedelta(days=1)

        from_ts = int(date.timestamp())
        to_ts   = int((date + timedelta(days=4)).timestamp())  # buffer for holidays

        url = "https://finnhub.io/api/v1/stock/candle"
        params = {
            "symbol":     ticker,
            "resolution": "D",
            "from":       from_ts,
            "to":         to_ts,
            "token":      FINNHUB_API_KEY,
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if data.get("s") == "ok" and data.get("c"):
            return data["c"][0]  # first closing price
    except Exception as e:
        log.debug(f"Price lookup failed for {ticker} on {date_str}: {e}")
    return None


def get_current_price(ticker: str) -> float | None:
    """Get current price for a ticker using Finnhub."""
    try:
        url = "https://finnhub.io/api/v1/quote"
        params = {"symbol": ticker, "token": FINNHUB_API_KEY}
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        price = data.get("c")
        return price if price and price > 0 else None
    except Exception as e:
        log.debug(f"Current price lookup failed for {ticker}: {e}")
    return None

# ── ANALYSIS ──────────────────────────────────────────────────────────────────

def enrich_trades(trades: list) -> list:
    """Add price performance data to each trade."""
    enriched = []
    tickers_done = {}  # cache current prices to avoid duplicate API calls

    for trade in trades:
        ticker = trade.get("ticker", "").strip().upper()

        # Skip options, bonds, or missing tickers
        if not ticker or ticker in ("--", "N/A") or len(ticker) > 5:
            continue

        trade_type = trade.get("type", "").lower()
        if "purchase" not in trade_type and "sale" not in trade_type:
            continue

        amount_str = trade.get("amount", "")
        estimated_value = parse_trade_value(amount_str)
        if estimated_value < MIN_TRADE_VALUE:
            continue

        trade_date = trade.get("transaction_date", "")

        # Get prices
        price_at_trade = get_price_on_date(ticker, trade_date)

        if ticker not in tickers_done:
            tickers_done[ticker] = get_current_price(ticker)
        current_price = tickers_done[ticker]

        # Calculate % move since trade
        price_move_pct = None
        if price_at_trade and current_price and price_at_trade > 0:
            price_move_pct = ((current_price - price_at_trade) / price_at_trade) * 100

        enriched.append({
            "representative": trade.get("representative", "Unknown"),
            "ticker":         ticker,
            "trade_type":     "BUY" if "purchase" in trade_type else "SELL",
            "trade_date":     trade_date,
            "estimated_value":estimated_value,
            "amount_str":     amount_str,
            "price_at_trade": price_at_trade,
            "current_price":  current_price,
            "price_move_pct": price_move_pct,
            "district":       trade.get("district", ""),
        })

        time.sleep(0.5)  # be gentle with the API

    return enriched


def find_notable_trades(enriched: list) -> list:
    """
    Sort trades by absolute price move since the trade.
    Flag large trades with significant price moves.
    """
    with_moves = [t for t in enriched if t["price_move_pct"] is not None]
    with_moves.sort(key=lambda x: abs(x["price_move_pct"]), reverse=True)
    return with_moves[:TOP_N_TRADES]

# ── FORMATTING ────────────────────────────────────────────────────────────────

def format_digest(notable: list, total_trades: int) -> str:
    now = datetime.now().strftime("%d %b %Y")
    lines = [
        f"🏛 <b>Politician Trade Tracker — {now}</b>",
        f"📊 {total_trades} trades in last {LOOKBACK_DAYS} days | Top {len(notable)} by price move\n",
    ]

    for i, t in enumerate(notable, 1):
        move = t["price_move_pct"]
        move_emoji = "📈" if move > 0 else "📉"
        suspicious = abs(move) >= MIN_PRICE_MOVE_PCT

        flag = " ⚠️ <b>NOTABLE</b>" if suspicious else ""

        lines.append(
            f"{i}. <b>{t['ticker']}</b> — {t['trade_type']} by {t['representative']}{flag}\n"
            f"   📅 {t['trade_date']} | 💰 {t['amount_str']}\n"
            f"   {move_emoji} Price move since trade: <b>{move:+.1f}%</b>"
            + (f" (${t['price_at_trade']:.2f} → ${t['current_price']:.2f})" 
               if t['price_at_trade'] and t['current_price'] else "")
            + "\n"
        )

    lines.append("\n⚠️ For informational purposes only. Not financial advice.")
    return "\n".join(lines)

# ── MAIN ──────────────────────────────────────────────────────────────────────

def run_digest() -> None:
    log.info("Running daily politician trade digest...")

    trades = fetch_trades()
    if not trades:
        log.warning("No trades fetched — skipping digest")
        return

    log.info("Enriching trades with price data (this takes a minute)...")
    enriched = enrich_trades(trades)
    log.info(f"{len(enriched)} trades enriched with price data")

    notable = find_notable_trades(enriched)
    message = format_digest(notable, len(enriched))

    send_telegram(message)
    log.info("Digest sent!")


def main():
    log.info("Politician Trade Tracker starting...")
    log.info(f"Daily digest at {DIGEST_TIME} | Lookback: {LOOKBACK_DAYS} days | Min trade: ${MIN_TRADE_VALUE:,}")

    # Run immediately on startup
    run_digest()

    # Then schedule daily
    schedule.every().day.at(DIGEST_TIME).do(run_digest)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
