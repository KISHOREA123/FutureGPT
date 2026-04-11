"""
Inline Keyboard UI for /coins command.
Shows 100 coins paginated (10 per page).
When user taps a coin → shows analysis options → asks timeframe → runs analysis.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from coins_list import COINS_100, COINS_PER_PAGE, TOTAL_PAGES, get_page


# ── Available timeframes for user selection ──────────────────
TIMEFRAME_OPTIONS = [
    ("15m", "15m"),
    ("1h",  "1h"),
    ("4h",  "4h"),
    ("1d",  "1d"),
]

# Human-readable labels for analysis types (used in TF selection header)
ANALYSIS_LABELS = {
    "analyze":    "📊 Full Analysis",
    "support":    "📍 Support & Resistance",
    "patterns":   "🕯 Candlestick Patterns",
    "liquidity":  "💧 Liquidity Zones",
    "fib":        "📐 Fibonacci",
    "ob":         "🧱 Order Blocks & FVG",
    "volatility": "📏 Volatility (ATR/BB)",
    "report":     "📋 Full Report",
    "trade":      "🎯 Trade Setup",
    "grade":      "🏆 Signal Grade",
    "summary":    "📑 Quick Summary",
}


def build_coins_keyboard(page: int = 1) -> InlineKeyboardMarkup:
    """
    Build the inline keyboard for a given page.

    Layout per page:
      Row 1-2: 5 coin buttons per row  (10 coins total, 2 rows)
      Row 3:   Navigation  [⬅ Prev]  [Page X/10]  [Next ➡]
      Row 4:   [🔍 Scan All]  [❌ Close]
    """
    page  = max(1, min(page, TOTAL_PAGES))
    coins = get_page(page)

    rows = []

    # ── Coin buttons (2 rows × 5 coins) ─────────────────────
    for i in range(0, COINS_PER_PAGE, 5):
        row = []
        for coin in coins[i : i + 5]:
            row.append(InlineKeyboardButton(
                text=coin,
                callback_data=f"select_coin:{coin}"
            ))
        rows.append(row)

    # ── Navigation row ────────────────────────────────────────
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅ Prev", callback_data=f"coins_page:{page-1}"))
    else:
        nav.append(InlineKeyboardButton("·", callback_data="noop"))  # placeholder

    nav.append(InlineKeyboardButton(
        f"📄 {page}/{TOTAL_PAGES}",
        callback_data="noop"
    ))

    if page < TOTAL_PAGES:
        nav.append(InlineKeyboardButton("Next ➡", callback_data=f"coins_page:{page+1}"))
    else:
        nav.append(InlineKeyboardButton("·", callback_data="noop"))

    rows.append(nav)

    # ── Action row ────────────────────────────────────────────
    rows.append([
        InlineKeyboardButton("🔍 Scan All", callback_data="scan_all"),
        InlineKeyboardButton("❌ Close",    callback_data="close_kb"),
    ])

    return InlineKeyboardMarkup(rows)


def build_coin_action_keyboard(coin: str) -> InlineKeyboardMarkup:
    """
    After selecting a coin, show analysis options.
    Each button now routes to timeframe selection first.
    Callback format: pick:{analysis_type}:{coin}
    """
    rows = [
        [
            InlineKeyboardButton("📍 S/R",        callback_data=f"pick:support:{coin}"),
            InlineKeyboardButton("🕯 Patterns",   callback_data=f"pick:patterns:{coin}"),
            InlineKeyboardButton("💧 Liquidity",  callback_data=f"pick:liquidity:{coin}"),
        ],
        [
            InlineKeyboardButton("📐 Fib",        callback_data=f"pick:fib:{coin}"),
            InlineKeyboardButton("🧱 OB/FVG",     callback_data=f"pick:ob:{coin}"),
            InlineKeyboardButton("📏 Volatility", callback_data=f"pick:volatility:{coin}"),
        ],
        [
            InlineKeyboardButton("📋 Report",     callback_data=f"pick:report:{coin}"),
            InlineKeyboardButton("🎯 Trade",      callback_data=f"pick:trade:{coin}"),
            InlineKeyboardButton("🏆 Grade",      callback_data=f"pick:grade:{coin}"),
        ],
        [
            InlineKeyboardButton("📊 Full Analysis", callback_data=f"pick:analyze:{coin}"),
            InlineKeyboardButton("📑 Summary",       callback_data=f"pick:summary:{coin}"),
        ],
        [
            InlineKeyboardButton("🔔 Watch",      callback_data=f"watch:{coin}"),
            InlineKeyboardButton("⬅ Back",        callback_data="coins_page:1"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def build_timeframe_keyboard(coin: str, analysis_type: str) -> InlineKeyboardMarkup:
    """
    Show timeframe selection buttons for a specific analysis.
    Callback format: tf:{analysis_type}:{coin}:{timeframe}
    """
    rows = [
        # Row 1: Individual timeframes
        [
            InlineKeyboardButton(
                text=label,
                callback_data=f"tf:{analysis_type}:{coin}:{tf_val}"
            )
            for label, tf_val in TIMEFRAME_OPTIONS
        ],
        # Row 2: All timeframes at once
        [
            InlineKeyboardButton(
                "⏱ All Timeframes",
                callback_data=f"tf:{analysis_type}:{coin}:all"
            ),
        ],
        # Row 3: Back to analysis options
        [
            InlineKeyboardButton("⬅ Back to Options", callback_data=f"select_coin:{coin}"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def timeframe_header(coin: str, analysis_type: str) -> str:
    """Header text shown above the timeframe selection keyboard."""
    label = ANALYSIS_LABELS.get(analysis_type, analysis_type)
    return (
        f"🪙 *{coin}* — {label}\n\n"
        f"Select a timeframe:"
    )


def coins_page_header(page: int) -> str:
    """Header text shown above the coin keyboard."""
    start = (page - 1) * COINS_PER_PAGE + 1
    end   = start + COINS_PER_PAGE - 1
    coins = get_page(page)
    coin_labels = "  ".join(coins)
    return (
        f"🪙 *Coin Browser* — Page {page}/{TOTAL_PAGES}\n"
        f"Coins #{start}–#{end}\n\n"
        f"`{coin_labels}`\n\n"
        f"_Tap a coin to select analysis ↓_"
    )
