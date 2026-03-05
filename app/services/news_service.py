"""
News Intelligence Service
==========================
Fetches Indian financial news and converts headlines into
actionable financial insights for the user.

Uses GNews API (free, 100 req/day) with smart static fallback.
Get free key at: https://gnews.io/
"""

import requests
from datetime import datetime

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ── Keyword → Financial Signal Map ─────────────────────────────────────────
SIGNAL_MAP = [
    {
        "keywords": ["petrol", "fuel", "diesel", "crude oil", "oil price"],
        "category": "transport",
        "icon": "⛽",
        "impact": "negative",
        "advice": "Fuel prices may rise. Consider reducing travel or carpooling to save on transport cost."
    },
    {
        "keywords": ["inflation", "cpi", "price rise", "price hike", "costlier", "expensive"],
        "category": "groceries",
        "icon": "📈",
        "impact": "negative",
        "advice": "Inflation is rising. Increase your monthly savings buffer by 5–10%."
    },
    {
        "keywords": ["vegetable", "tomato", "onion", "potato", "food price", "agri", "crop"],
        "category": "vegetables",
        "icon": "🥦",
        "impact": "negative",
        "advice": "Vegetable prices may spike. Stock up essentials or buy in bulk this week."
    },
    {
        "keywords": ["rbi", "repo rate", "interest rate", "monetary policy", "emi", "loan rate"],
        "category": "utilities",
        "icon": "🏦",
        "impact": "neutral",
        "advice": "RBI rate change detected. Review your loan EMIs and FD returns."
    },
    {
        "keywords": ["nifty", "sensex", "stock market", "bull", "rally", "equity", "bse"],
        "category": "assets",
        "icon": "📊",
        "impact": "positive",
        "advice": "Market is active. Consider reviewing your equity or SIP investments."
    },
    {
        "keywords": ["gold", "mcx gold", "sovereign gold", "gold price"],
        "category": "assets",
        "icon": "🥇",
        "impact": "positive",
        "advice": "Gold prices are moving. Consider gold as an inflation hedge in your portfolio."
    },
    {
        "keywords": ["recession", "slowdown", "gdp fall", "job loss", "layoff", "unemployment"],
        "category": "savings",
        "icon": "⚠️",
        "impact": "negative",
        "advice": "Economic slowdown signals detected. Build a 6-month emergency fund as a safety net."
    },
    {
        "keywords": ["rain", "monsoon", "drought", "flood", "weather", "cyclone"],
        "category": "vegetables",
        "icon": "🌧️",
        "impact": "negative",
        "advice": "Extreme weather may affect food supply. Grocery prices could increase soon."
    },
    {
        "keywords": ["tax", "income tax", "gst", "budget", "finance minister", "deduction"],
        "category": "savings",
        "icon": "📋",
        "impact": "neutral",
        "advice": "Tax or budget news detected. Review your tax-saving investments like PPF, ELSS."
    },
    {
        "keywords": ["upi", "cashback", "offer", "discount", "payment"],
        "category": "savings",
        "icon": "💳",
        "impact": "positive",
        "advice": "New payment offers available. Use UPI cashback deals to save on daily purchases."
    },
]

# ── Static fallback insights (shown when news fetch fails) ──────────────────
STATIC_INSIGHTS = [
    {
        "headline": "General financial tip: Track your monthly expenses",
        "icon": "💡",
        "impact": "positive",
        "category": "savings",
        "advice": "Review your top 3 spending categories and set a budget limit for each."
    },
    {
        "headline": "Investment reminder",
        "icon": "📊",
        "impact": "positive",
        "category": "assets",
        "advice": "Consistent SIP investments beat lump-sum investing over the long term."
    },
    {
        "headline": "Emergency fund check",
        "icon": "🏦",
        "impact": "neutral",
        "category": "savings",
        "advice": "Make sure you have at least 3–6 months of expenses saved as an emergency fund."
    },
    {
        "headline": "Food cost tip",
        "icon": "🥦",
        "impact": "neutral",
        "category": "groceries",
        "advice": "Plan weekly meals in advance to avoid impulse food purchases and reduce waste."
    },
    {
        "headline": "Transport savings tip",
        "icon": "⛽",
        "impact": "neutral",
        "category": "transport",
        "advice": "Combining errands into single trips can reduce fuel costs by up to 20%."
    },
]


def fetch_gnews_headlines(api_key: str) -> list:
    """Fetch headlines from GNews API (free tier)."""
    url = "https://gnews.io/api/v4/search"
    params = {
        "q": "india economy inflation finance market",
        "lang": "en",
        "country": "in",
        "max": 10,
        "apikey": api_key
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=8)
    data = resp.json()
    return [a["title"] for a in data.get("articles", [])]


def fetch_yahoo_finance_headlines() -> list:
    """Fallback: scrape Yahoo Finance India headlines."""
    try:
        url = "https://query1.finance.yahoo.com/v1/finance/trending/IN"
        resp = requests.get(url, headers=HEADERS, timeout=6)
        data = resp.json()
        quotes = data.get("finance", {}).get("result", [{}])[0].get("quotes", [])
        return [q.get("shortName", "") for q in quotes if q.get("shortName")]
    except Exception:
        return []


def analyze_headlines(headlines: list) -> list:
    """Match headlines to financial signals."""
    seen_categories = set()
    insights = []
    for headline in headlines:
        text = headline.lower()
        for signal in SIGNAL_MAP:
            if signal["category"] in seen_categories:
                continue
            if any(kw in text for kw in signal["keywords"]):
                insights.append({
                    "headline": headline,
                    "icon": signal["icon"],
                    "impact": signal["impact"],
                    "category": signal["category"],
                    "advice": signal["advice"],
                })
                seen_categories.add(signal["category"])
                break
    return insights


def get_news_insights(gnews_api_key: str = "") -> dict:
    """
    Main function — fetches news and returns structured insights.
    Falls back to static insights if news fetch fails.
    """
    fetched_at = datetime.now().strftime("%d %b %Y, %I:%M %p")
    headlines = []
    source = "static"

    # Try GNews if key provided
    if gnews_api_key:
        try:
            headlines = fetch_gnews_headlines(gnews_api_key)
            if headlines:
                source = "gnews"
        except Exception as e:
            print(f"[NEWS] GNews failed: {e}")

    # Try Yahoo Finance trending as fallback
    if not headlines:
        try:
            headlines = fetch_yahoo_finance_headlines()
            if headlines:
                source = "yahoo"
        except Exception as e:
            print(f"[NEWS] Yahoo fallback failed: {e}")

    # Analyze headlines if we got any
    insights = analyze_headlines(headlines) if headlines else []

    # Fill remaining slots with static insights
    used_categories = {i["category"] for i in insights}
    for s in STATIC_INSIGHTS:
        if len(insights) >= 5:
            break
        if s["category"] not in used_categories:
            insights.append(s)
            used_categories.add(s["category"])

    return {
        "status": "ok",
        "source": source,
        "fetched_at": fetched_at,
        "total_headlines": len(headlines),
        "insights": insights[:5],
    }