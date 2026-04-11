"""
Master list of 100 USDT pairs for the /coins keyboard UI.
Grouped into 10 pages, 10 coins per page.
"""

COINS_100 = [
    # Page 1 — Majors
    "BTC", "ETH", "BNB", "SOL", "XRP",
    "DOGE", "ADA", "TRX", "AVAX", "TON",
    # Page 2 — Large caps
    "LINK", "DOT", "MATIC", "LTC", "UNI",
    "ATOM", "XLM", "BCH", "NEAR", "APT",
    # Page 3 — DeFi
    "ARB", "OP", "AAVE", "MKR", "CRV",
    "COMP", "SNX", "INJ", "GMX", "DYDX",
    # Page 4 — Layer 1s
    "FTM", "ALGO", "HBAR", "EOS", "VET",
    "ICP", "EGLD", "FIL", "FLOW", "XTZ",
    # Page 5 — AI / Trending
    "FET", "AGIX", "OCEAN", "RNDR", "WLD",
    "TAO", "ARKM", "GRT", "LPT", "NMR",
    # Page 6 — Gaming / Metaverse
    "AXS", "SAND", "MANA", "ENJ", "GALA",
    "IMX", "GODS", "YGG", "ALICE", "CHR",
    # Page 7 — Exchange tokens
    "OKB", "HT", "KCS", "GT", "CRO",
    "MX", "WOO", "LUNC", "FTT", "BGB",
    # Page 8 — Mid caps
    "SUI", "SEI", "TIA", "PYTH", "JTO",
    "MEME", "BONK", "WIF", "PEPE", "FLOKI",
    # Page 9 — Infrastructure
    "STX", "ROSE", "CFX", "MASK", "API3",
    "BAND", "REN", "ANT", "NKN", "STORJ",
    # Page 10 — Others
    "ZEC", "DASH", "XMR", "WAVES", "ZIL",
    "ONT", "IOTA", "QTUM", "ICX", "DCR",
]

COINS_PER_PAGE = 10
TOTAL_PAGES    = len(COINS_100) // COINS_PER_PAGE  # 10


def get_page(page: int) -> list[str]:
    """Return list of coins for a given page (1-indexed)."""
    page = max(1, min(page, TOTAL_PAGES))
    start = (page - 1) * COINS_PER_PAGE
    return COINS_100[start : start + COINS_PER_PAGE]
