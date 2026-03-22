"""
handlers/analyze_handler.py — Coin Analyze / Search feature.

Callbacks:
  action:analyze       → entry search screen
  analyze:page:<N>     → paginated coin grid (page N)
  analyze:gainers      → top gainers card
  analyze:losers       → top losers card
  analyze:movers       → refresh top movers
  analyze:search       → FSM: wait for typed coin name
  analyze:<SYM>        → full analysis for a coin
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.analyze_keyboard import (
    analyze_search_keyboard,
    analyze_page_keyboard,
    analyze_result_keyboard,
    analyze_movers_keyboard,
    analyze_fsm_keyboard,
    ALL_COINS,
)
from services import (
    get_single_price, get_single_signal,
    InvalidSymbolError, VALID_SYMBOLS, COIN_META,
)
from services.price_service import get_top_movers, format_top_movers
from services.indicator_service import compute_indicators
from services.sentiment_service import compute_sentiment, format_sentiment_card
from services.pattern_service import detect_patterns, format_patterns_card

logger = logging.getLogger(__name__)
router = Router(name="analyze")


# ── FSM ───────────────────────────────────────────────────────────────────────

class AnalyzeStates(StatesGroup):
    waiting_for_coin = State()


# ── Name → ticker resolver ────────────────────────────────────────────────────

_NAME_ALIASES: dict[str, str] = {
    "bitcoin": "BTC", "btc": "BTC",
    "ethereum": "ETH", "eth": "ETH", "ether": "ETH",
    "bnb": "BNB", "binance": "BNB",
    "solana": "SOL", "sol": "SOL",
    "xrp": "XRP", "ripple": "XRP",
    "cardano": "ADA", "ada": "ADA",
    "dogecoin": "DOGE", "doge": "DOGE",
    "ton": "TON", "toncoin": "TON",
    "avalanche": "AVAX", "avax": "AVAX",
    "polkadot": "DOT", "dot": "DOT",
    "polygon": "POL", "pol": "POL", "matic": "POL",
    "litecoin": "LTC", "ltc": "LTC",
    "chainlink": "LINK", "link": "LINK",
    "uniswap": "UNI", "uni": "UNI",
    "cosmos": "ATOM", "atom": "ATOM",
    "near": "NEAR", "near protocol": "NEAR",
    "pepe": "PEPE",
    "shiba": "SHIB", "shib": "SHIB", "shiba inu": "SHIB",
    "arbitrum": "ARB", "arb": "ARB",
    "optimism": "OP", "op": "OP",
    "aptos": "APT", "apt": "APT",
    "sui": "SUI",
    "tron": "TRX", "trx": "TRX",
    "kaspa": "KAS", "kas": "KAS",
    "floki": "FLOKI",
    "bonk": "BONK",
    "notcoin": "NOT", "not": "NOT",
    "gala": "GALA",
    "sandbox": "SAND", "sand": "SAND",
    "chiliz": "CHZ", "chz": "CHZ",
    "brett": "BRETT",
    "wif": "WIF", "dogwifhat": "WIF",
    "injective": "INJ", "inj": "INJ",
    "fetch": "FET", "fet": "FET",
    "render": "RENDER", "rndr": "RENDER",
    "immutable": "IMX", "imx": "IMX",
    "the graph": "GRT", "grt": "GRT",
    "aave": "AAVE",
    "maker": "MKR", "mkr": "MKR",
    "filecoin": "FIL", "fil": "FIL",
    "internet computer": "ICP", "icp": "ICP",
    "vechain": "VET", "vet": "VET",
    "algorand": "ALGO", "algo": "ALGO",
    "hedera": "HBAR", "hbar": "HBAR",
    "stellar": "XLM", "xlm": "XLM",
    "ethereum classic": "ETC", "etc": "ETC",
    "decentraland": "MANA", "mana": "MANA",
    "axie": "AXS", "axs": "AXS",
    "curve": "CRV", "crv": "CRV",
    "lido": "LDO", "ldo": "LDO",
    "ens": "ENS",
    "synthetix": "SNX", "snx": "SNX",
    "pancakeswap": "CAKE", "cake": "CAKE",
    "zcash": "ZEC", "zec": "ZEC",
    "dash": "DASH",
    "monero": "XMR", "xmr": "XMR",
    "eos": "EOS",
    "tezos": "XTZ", "xtz": "XTZ",
    "theta": "THETA",
    "thorchain": "RUNE", "rune": "RUNE",
    "multiversx": "EGLD", "egld": "EGLD",
}

_ALL_ANALYZE_SYMBOLS: set[str] = VALID_SYMBOLS | set(ALL_COINS)


def _resolve_symbol(text: str) -> str | None:
    cleaned = text.strip().upper()
    if cleaned in _ALL_ANALYZE_SYMBOLS:
        return cleaned
    return _NAME_ALIASES.get(text.strip().lower())


# ── Screen texts ──────────────────────────────────────────────────────────────

SEARCH_TEXT = (
    "🔍 <b>Search Any Coin:</b>\n\n"
    "💬 <b>Type</b> any coin or ticker below\n"
    "<i>E.g: 'BTC' or 'Bitcoin'</i>"
)

FSM_PROMPT_TEXT = (
    "🔍 <b>Search Any Coin:</b>\n\n"
    "💬 <b>Type</b> any coin or ticker below\n"
    "<i>E.g: 'BTC' or 'Bitcoin'</i>\n\n"
    "⌨️ <i>Type your coin name now…</i>"
)


# ── Edit helper ───────────────────────────────────────────────────────────────

async def _edit(query: CallbackQuery, text: str, keyboard) -> None:
    try:
        await query.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await query.message.answer(text, reply_markup=keyboard)


# ── Entry ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "action:analyze")
async def cb_analyze_entry(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await query.answer()
    await _edit(query, SEARCH_TEXT, analyze_search_keyboard())


# ── Paginated coin grid ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("analyze:page:"))
async def cb_analyze_page(query: CallbackQuery) -> None:
    page = int(query.data.split(":")[-1])
    await query.answer()
    await _edit(query, SEARCH_TEXT, analyze_page_keyboard(page))


# ── Top Gainers ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.in_({"analyze:gainers", "analyze:losers", "analyze:movers"}))
async def cb_top_movers(query: CallbackQuery) -> None:
    await query.answer("⏳ Fetching market data…")
    logger.info("User %s → top movers (%s)", query.from_user.id, query.data)

    await _edit(
        query,
        "⏳ <b>Fetching top movers…</b>\n<code>▓▓▓▓▓░░░░░  50%</code>",
        analyze_movers_keyboard(),
    )

    data = await get_top_movers()
    text = format_top_movers(data)
    await _edit(query, text, analyze_movers_keyboard())


# ── No-op (page indicator button) ─────────────────────────────────────────────

@router.callback_query(F.data == "noop")
async def cb_noop(query: CallbackQuery) -> None:
    await query.answer()   # dismiss spinner, do nothing


# ── FSM entry ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "analyze:search")
async def cb_analyze_search_fsm(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    await state.set_state(AnalyzeStates.waiting_for_coin)
    await _edit(query, FSM_PROMPT_TEXT, analyze_fsm_keyboard())


# ── Coin button tap ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("analyze:"))
async def cb_analyze_coin(query: CallbackQuery) -> None:
    raw = query.data.split(":", 1)[1]
    # Guard: skip sub-commands handled by dedicated handlers above
    if raw in ("more", "search", "gainers", "losers", "movers") or raw.startswith("page:"):
        return

    symbol = raw.upper()
    await query.answer(f"🔍 Analysing {symbol}…")
    logger.info("User %s → analyze:%s", query.from_user.id, symbol)
    await _run_analysis(query.message, symbol, edit=True)


# ── FSM message handler ────────────────────────────────────────────────────────

@router.message(AnalyzeStates.waiting_for_coin)
async def msg_analyze_coin(message: Message, state: FSMContext) -> None:
    raw    = (message.text or "").strip()
    symbol = _resolve_symbol(raw)

    if not symbol:
        await message.answer(
            f"⚠️ <b>Coin not found:</b> <code>{raw}</code>\n\n"
            "<i>Try: BTC, ETH, SOL, or full names like 'Bitcoin'</i>",
            reply_markup=analyze_fsm_keyboard(),
        )
        return

    await state.clear()
    placeholder = await message.answer(
        f"⏳ <b>Analysing {symbol}…</b>\n<i>Fetching price + computing indicators</i>"
    )
    await _run_analysis(placeholder, symbol, edit=True)


# ── /analyze command ──────────────────────────────────────────────────────────

@router.message(Command("analyze"))
async def cmd_analyze(message: Message, state: FSMContext) -> None:
    parts  = (message.text or "").split(maxsplit=1)
    raw    = parts[1].strip() if len(parts) > 1 else ""
    symbol = _resolve_symbol(raw) if raw else None

    if symbol:
        placeholder = await message.answer(f"⏳ <b>Analysing {symbol}…</b>")
        await _run_analysis(placeholder, symbol, edit=True)
    else:
        await state.clear()
        await message.answer(SEARCH_TEXT, reply_markup=analyze_search_keyboard())


# ── Core analysis runner ──────────────────────────────────────────────────────

async def _run_analysis(msg: Message, symbol: str, edit: bool = True) -> None:
    meta = COIN_META.get(symbol, {"icon": "🪙", "name": symbol})

    loading = (
        f"⏳ <b>Analysing {meta['icon']} {meta['name']} ({symbol})…</b>\n\n"
        f"<i>Price · RSI/MACD/EMA · Sentiment · Chart Patterns</i>\n\n"
        f"<code>▓▓▓▓▓▓░░░░  60%</code>"
    )
    try:
        if edit:
            await msg.edit_text(loading)
        else:
            await msg.answer(loading)
    except Exception:
        pass

    price_text = signal_text = price_err = signal_err = None
    sentiment_card = pattern_card = None

    try:
        price_text = await get_single_price(symbol)
    except InvalidSymbolError:
        price_err = f"⚠️ <b>Unknown symbol:</b> <code>{symbol}</code>"
    except Exception:
        price_err = "⚠️ Price unavailable"

    try:
        signal_text = await get_single_signal(symbol)
    except Exception:
        signal_err = "⚠️ Signal unavailable"

    # Sentiment + Patterns (reuse OHLCV data already fetched for indicators)
    try:
        from services.indicator_service import fetch_ohlcv, apply_indicators_to_df
        ind           = await compute_indicators(symbol)
        sentiment     = compute_sentiment(ind)
        sentiment_card = format_sentiment_card(sentiment, symbol)

        df           = await fetch_ohlcv(symbol)
        df           = apply_indicators_to_df(df)
        patterns     = detect_patterns(df)
        pattern_card = format_patterns_card(patterns)
    except Exception as exc:
        logger.debug("Sentiment/pattern error for %s: %s", symbol, exc)

    card = _build_card(symbol, meta, price_text, signal_text,
                       price_err, signal_err, sentiment_card, pattern_card)

    try:
        await msg.edit_text(card, reply_markup=analyze_result_keyboard(symbol))
    except Exception:
        await msg.answer(card, reply_markup=analyze_result_keyboard(symbol))


def _build_card(symbol, meta, price_text, signal_text,
                price_err, signal_err, sentiment_card=None, pattern_card=None) -> str:
    icon = meta.get("icon", "🪙")
    name = meta.get("name", symbol)

    lines = [
        f"📊 <b>{icon} {name} ({symbol}) — Full Analysis</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if price_text:
        price_lines = price_text.strip().split("\n")
        lines += price_lines[2:] if len(price_lines) > 2 else price_lines
    elif price_err:
        lines.append(price_err)

    lines.append("━━━━━━━━━━━━━━━━━━━━━━")

    if signal_text:
        signal_lines = signal_text.strip().split("\n")
        lines += signal_lines[2:] if len(signal_lines) > 2 else signal_lines
    elif signal_err:
        lines.append(signal_err)

    if sentiment_card:
        lines.append("")
        lines.append(sentiment_card)

    if pattern_card:
        lines.append("")
        lines.append(pattern_card)

    return "\n".join(lines)