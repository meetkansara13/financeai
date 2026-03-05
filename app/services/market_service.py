"""
Market Data Service
===================
Fetches real-time prices from Yahoo Finance (free, no API key needed).
Symbols used:
  ^NSEI     = Nifty 50
  GC=F      = Gold Futures (USD) → converted to INR
  NIFTYBEES.NS = HDFC Nifty 50 ETF
  BTC-USD   = Bitcoin → converted to INR
  GOLDBEES.NS   = Nippon Gold BeES ETF (proxy for gold in INR)
"""

import requests
from datetime import datetime

# USD to INR approximate rate (updated periodically)
# We also fetch this live from Yahoo
USD_INR_FALLBACK = 83.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def fetch_yahoo(symbol: str) -> dict:
    """Fetch quote summary from Yahoo Finance v8 API."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        data = r.json()
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price     = meta.get("regularMarketPrice", 0)
        prev      = meta.get("chartPreviousClose") or meta.get("previousClose", price)
        currency  = meta.get("currency", "INR")
        change_pct = ((price - prev) / prev * 100) if prev else 0
        return {
            "price": price,
            "prev":  prev,
            "change_pct": round(change_pct, 2),
            "currency": currency,
            "ok": True
        }
    except Exception as e:
        print(f"[MARKET] Yahoo fetch error for {symbol}: {e}")
        return {"price": 0, "prev": 0, "change_pct": 0, "currency": "INR", "ok": False}


def get_usd_inr() -> float:
    """Get live USD/INR rate."""
    d = fetch_yahoo("USDINR=X")
    return d["price"] if d["ok"] and d["price"] > 0 else USD_INR_FALLBACK


def fmt_inr(val: float) -> str:
    """Format number as Indian currency string."""
    if val >= 10_000_000:
        return f"₹{val/10_000_000:.1f}Cr"
    elif val >= 100_000:
        return f"₹{val/100_000:.1f}L"
    elif val >= 1000:
        return f"₹{int(val):,}"
    else:
        return f"₹{val:.2f}"


def get_market_data() -> list:
    """
    Returns list of investment instruments with live prices.
    Falls back to static data if Yahoo is unavailable.
    """
    usd_inr = get_usd_inr()

    instruments = []

    # 1. Nifty 50
    nifty = fetch_yahoo("^NSEI")
    instruments.append({
        "name":  "Nifty 50",
        "ico":   "📊",
        "val":   f"{nifty['price']:,.0f}" if nifty["ok"] else "—",
        "chg":   f"{nifty['change_pct']:+.2f}%",
        "up":    nifty["change_pct"] >= 0,
        "rec":   "buy" if nifty["change_pct"] > -0.5 else "hold",
        "note":  "Nifty 50 live index. SIP recommended for long-term.",
        "live":  nifty["ok"]
    })

    # 2. Gold (via MCX Gold ETF proxy — GOLDBEES)
    gold = fetch_yahoo("GOLDBEES.NS")
    gold_price = gold["price"] * 100 if gold["ok"] else 0  # per unit ≈ 1g, *100 = 10g approx
    instruments.append({
        "name": "Gold (10g)",
        "ico":  "🥇",
        "val":  fmt_inr(gold_price) if gold["ok"] else "—",
        "chg":  f"{gold['change_pct']:+.2f}%",
        "up":   gold["change_pct"] >= 0,
        "rec":  "hold",
        "note": "Inflation hedge. 5–10% of portfolio ideal.",
        "live": gold["ok"]
    })

    # 3. HDFC Nifty ETF
    hdfc = fetch_yahoo("NIFTYBEES.NS")
    instruments.append({
        "name": "Nifty BeES ETF",
        "ico":  "🏦",
        "val":  f"₹{hdfc['price']:.1f}" if hdfc["ok"] else "—",
        "chg":  f"{hdfc['change_pct']:+.2f}%",
        "up":   hdfc["change_pct"] >= 0,
        "rec":  "buy" if hdfc["change_pct"] > -0.5 else "hold",
        "note": "Nippon Nifty BeES ETF. Low cost, high liquidity.",
        "live": hdfc["ok"]
    })

    # 4. Fixed Deposit (static — no market price)
    instruments.append({
        "name": "Fixed Deposit",
        "ico":  "🏛️",
        "val":  "7.1% p.a.",
        "chg":  "Stable",
        "up":   True,
        "rec":  "hold",
        "note": "Safe option if goal < 2 years away.",
        "live": False
    })

    # 5. Bitcoin
    btc = fetch_yahoo("BTC-USD")
    btc_inr = btc["price"] * usd_inr if btc["ok"] else 0
    instruments.append({
        "name": "Bitcoin (BTC)",
        "ico":  "₿",
        "val":  fmt_inr(btc_inr) if btc["ok"] else "—",
        "chg":  f"{btc['change_pct']:+.2f}%",
        "up":   btc["change_pct"] >= 0,
        "rec":  "wait",
        "note": "High risk. Max 2–3% of portfolio only.",
        "live": btc["ok"]
    })

    # 6. Real Estate (static signal)
    instruments.append({
        "name": "Real Estate",
        "ico":  "🏗️",
        "val":  "+15–20% YoY",
        "chg":  "+18%",
        "up":   True,
        "rec":  "buy",
        "note": "Long term. Needs high capital commitment.",
        "live": False
    })

    # 7. Mutual Fund — Nifty Flexicap proxy via UTI Nifty 50
    mf = fetch_yahoo("0P0001EJKP.BO")
    instruments.append({
        "name": "Flexi Cap MF",
        "ico":  "📈",
        "val":  f"₹{mf['price']:.1f}" if mf["ok"] else "Flexi Cap",
        "chg":  f"{mf['change_pct']:+.2f}%" if mf["ok"] else "+14% YTD",
        "up":   mf["change_pct"] >= 0 if mf["ok"] else True,
        "rec":  "buy",
        "note": "Best for 3+ year horizon. Diversified equity.",
        "live": mf["ok"]
    })

    # 8. PPF (static)
    instruments.append({
        "name": "PPF",
        "ico":  "🏛️",
        "val":  "7.1% p.a.",
        "chg":  "Tax Free",
        "up":   True,
        "rec":  "buy",
        "note": "15yr lock-in. Tax-free returns under 80C.",
        "live": False
    })

    return instruments


def get_market_data_cached() -> list:
    """
    Simple in-memory cache — refreshes every 5 minutes.
    Avoids hammering Yahoo Finance on every page load.
    """
    now = datetime.utcnow()
    cache = get_market_data_cached

    if not hasattr(cache, "_data") or not hasattr(cache, "_ts"):
        cache._data = None
        cache._ts   = None

    if cache._data is None or (now - cache._ts).seconds > 300:
        print("[MARKET] Fetching fresh market data...")
        cache._data = get_market_data()
        cache._ts   = now
    else:
        print("[MARKET] Serving cached market data.")

    return cache._data