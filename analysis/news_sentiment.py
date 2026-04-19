"""
News Sentiment Analyzer
Scrapes crypto news from RSS feeds and scores sentiment using keyword analysis.
Supports coin-specific filtering and aggregate sentiment scoring.
"""
import re
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from config import NEWS_TIMEOUT

logger = logging.getLogger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ── RSS Feed Sources ─────────────────────────────────────────
RSS_FEEDS = [
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "emoji": "📰"},
    {"name": "CoinTelegraph", "url": "https://cointelegraph.com/rss", "emoji": "📡"},
    {"name": "Bitcoin Magazine", "url": "https://bitcoinmagazine.com/feed", "emoji": "🗞"},
]

# ── Ticker → Full Names (for headline matching) ─────────────
TICKER_MAP = {
    "BTC": ["bitcoin", "btc"], "ETH": ["ethereum", "eth", "ether"],
    "SOL": ["solana", "sol"], "BNB": ["bnb", "binance coin"],
    "XRP": ["xrp", "ripple"], "DOGE": ["doge", "dogecoin"],
    "ADA": ["cardano", "ada"], "AVAX": ["avalanche", "avax"],
    "DOT": ["polkadot", "dot"], "LINK": ["chainlink", "link"],
    "MATIC": ["polygon", "matic"], "UNI": ["uniswap", "uni"],
    "ATOM": ["cosmos", "atom"], "ARB": ["arbitrum", "arb"],
    "OP": ["optimism"], "NEAR": ["near protocol", "near"],
    "APT": ["aptos", "apt"], "SUI": ["sui"],
    "SEI": ["sei"], "TIA": ["celestia", "tia"],
    "INJ": ["injective", "inj"], "FET": ["fetch.ai", "fetch"],
    "RNDR": ["render", "rndr"], "WLD": ["worldcoin", "wld"],
}

# ── Sentiment keyword dictionaries ──────────────────────────
BULLISH_KEYWORDS = {
    "rally": 3, "bullish": 3, "surge": 3, "soar": 3, "breakout": 3,
    "pump": 2, "moon": 2, "all-time high": 3, "ath": 3, "gains": 2,
    "adoption": 2, "upgrade": 2, "partnership": 2, "buy": 1,
    "accumulate": 2, "institutional": 2, "whale": 1, "launch": 1,
    "approval": 3, "etf": 2, "bullrun": 3, "growth": 2,
    "positive": 1, "rising": 2, "skyrocket": 3, "recovery": 2,
    "demand": 2, "innovation": 1, "outperform": 2,
}

BEARISH_KEYWORDS = {
    "crash": 3, "bearish": 3, "dump": 3, "plunge": 3, "decline": 2,
    "sell-off": 3, "selloff": 3, "collapse": 3, "liquidation": 2,
    "hack": 3, "exploit": 3, "scam": 3, "fraud": 3, "ban": 3,
    "regulation": 1, "crackdown": 2, "fear": 2, "panic": 2,
    "bubble": 2, "warning": 1, "risk": 1, "lawsuit": 2,
    "sec": 1, "investigation": 2, "bankruptcy": 3, "insolvency": 3,
    "rug pull": 3, "rugpull": 3, "loss": 1, "negative": 1,
    "falling": 2, "correction": 1, "fud": 2,
}


def _fetch_feed(feed_info: dict) -> list:
    """Fetch and parse a single RSS feed."""
    if not HAS_REQUESTS:
        return []

    articles = []
    try:
        resp = requests.get(feed_info["url"], timeout=NEWS_TIMEOUT)
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.content)
        items = root.findall(".//item")

        for item in items[:15]:  # Last 15 articles per feed
            title = item.findtext("title", "").strip()
            pub_date = item.findtext("pubDate", "")
            link = item.findtext("link", "")
            description = item.findtext("description", "").strip()

            if title:
                articles.append({
                    "title": title,
                    "description": description[:200],
                    "source": feed_info["name"],
                    "emoji": feed_info["emoji"],
                    "link": link,
                    "pub_date": pub_date,
                })
    except Exception as e:
        logger.warning(f"Failed to fetch {feed_info['name']}: {e}")

    return articles


def _score_headline(text: str) -> tuple:
    """Score a headline/description for sentiment."""
    text_lower = text.lower()
    bullish_score = 0
    bearish_score = 0
    matched_keywords = []

    for kw, weight in BULLISH_KEYWORDS.items():
        if kw in text_lower:
            bullish_score += weight
            matched_keywords.append(f"🟢 {kw}")

    for kw, weight in BEARISH_KEYWORDS.items():
        if kw in text_lower:
            bearish_score += weight
            matched_keywords.append(f"🔴 {kw}")

    return bullish_score, bearish_score, matched_keywords


def _filter_for_coin(articles: list, symbol: str) -> list:
    """Filter articles relevant to a specific coin."""
    symbol_upper = symbol.upper().replace("/USDT", "")
    keywords = TICKER_MAP.get(symbol_upper, [symbol_upper.lower()])

    filtered = []
    for article in articles:
        text = f"{article['title']} {article.get('description', '')}".lower()
        if any(kw in text for kw in keywords):
            filtered.append(article)

    return filtered


def get_news_sentiment(symbol: str = "") -> dict:
    """
    Fetch news and compute sentiment score.

    Args:
        symbol: Optional coin symbol to filter news for

    Returns:
        dict with sentiment score, articles, and summary
    """
    if not HAS_REQUESTS:
        return {
            "sentiment": "N/A",
            "score": 0,
            "articles": [],
            "error": "requests library not installed",
        }

    # Fetch from all feeds
    all_articles = []
    for feed in RSS_FEEDS:
        articles = _fetch_feed(feed)
        all_articles.extend(articles)

    if not all_articles:
        return {
            "sentiment": "neutral",
            "score": 0,
            "confidence": 0,
            "articles": [],
            "label": "📰 No news data available",
        }

    # Filter for specific coin if provided
    if symbol:
        relevant = _filter_for_coin(all_articles, symbol)
    else:
        relevant = all_articles

    # Score each article
    total_bullish = 0
    total_bearish = 0
    scored_articles = []

    for article in relevant:
        text = f"{article['title']} {article.get('description', '')}"
        bull, bear, keywords = _score_headline(text)
        total_bullish += bull
        total_bearish += bear

        if bull > 0 or bear > 0:
            scored_articles.append({
                "title": article["title"],
                "source": article["source"],
                "emoji": article["emoji"],
                "sentiment": "bullish" if bull > bear else "bearish" if bear > bull else "neutral",
                "bull_score": bull,
                "bear_score": bear,
            })

    # Compute aggregate sentiment
    total = total_bullish + total_bearish
    if total == 0:
        sentiment = "neutral"
        score = 0
        confidence = 0
    else:
        score = total_bullish - total_bearish
        confidence = round(abs(score) / total * 100, 1)
        if score > 3:
            sentiment = "bullish"
        elif score < -3:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

    # Label
    if sentiment == "bullish":
        label = f"🟢 BULLISH Sentiment (score: +{score})"
    elif sentiment == "bearish":
        label = f"🔴 BEARISH Sentiment (score: {score})"
    else:
        label = f"⚪ NEUTRAL Sentiment (score: {score})"

    return {
        "sentiment": sentiment,
        "score": score,
        "confidence": confidence,
        "bullish_total": total_bullish,
        "bearish_total": total_bearish,
        "label": label,
        "articles": scored_articles[:10],
        "total_articles": len(all_articles),
        "relevant_articles": len(relevant),
        "symbol": symbol,
    }
