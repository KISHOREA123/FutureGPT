"""
services/ai_service.py — FutureGPT AI chat with per-user conversation memory.

Full pipeline per request:
  1. Load the user's Conversation from conversation_store (last MAX_TURNS pairs)
  2. Build:  [system_prompt]  +  [history turns]  +  [new question]
  3. POST to OpenAI /v1/chat/completions  (or return a smart mock if key absent)
  4. Persist the new (question, answer) turn back to the store
  5. Return a formatted HTML card ready for Telegram

System prompt enforces:
  • Concise, emoji-rich crypto responses (≤ 3 sentences)
  • Practical and actionable — no vague non-answers
  • No financial guarantees, no invented data
  • "Data unclear 🤷" when genuinely uncertain
"""

import logging
import re
import aiohttp

from config import settings
from services.conversation_store import (
    get_conversation,
    clear_conversation,
    conversation_length,
    has_conversation,
    MAX_TURNS,
)

logger = logging.getLogger(__name__)

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are FutureGPT, a crypto trading assistant inside a Telegram bot.

RULES — follow every one, every time:
1. Max 3 sentences per answer. Be concise and direct.
2. Use 1–3 emojis naturally woven into the text — not stacked at the start.
3. Be practical: give specific, actionable insight the user can act on.
4. Never guarantee profits or promise exact price targets.
5. If data is ambiguous or you lack confidence → reply with exactly:
   "Data unclear 🤷" followed by one sentence explaining what's missing.
6. Never repeat the user's question back to them.
7. Crypto-only: politely redirect off-topic questions back to crypto.
8. Use context from previous messages in this conversation when relevant.

GOOD: "BTC looks slightly overbought 📈 Wait for a pullback near $65k support before adding."
BAD:  "I think Bitcoin could potentially go up or down depending on market conditions."
BAD:  "Great question! Bitcoin is a decentralised digital currency created in 2009..."
"""

# ── OpenAI config ─────────────────────────────────────────────────────────────

OPENAI_URL      = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL    = "gpt-4o-mini"
MAX_TOKENS      = 180       # tight cap keeps replies short and snappy
TEMPERATURE     = 0.5       # balanced: creative but grounded
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)

# ── Smart mock responses ──────────────────────────────────────────────────────
# Shown when OPENAI_API_KEY is not set — keyword-matched, realistic responses.

_MOCK_RULES: list[tuple[list[str], str]] = [
    (
        ["buy", "should i", "entry", "btc", "bitcoin"],
        "BTC is consolidating near key support 📊 "
        "RSI is neutral — no clear entry signal yet. "
        "Wait for a confirmed breakout above resistance or a dip to $60k before sizing in.",
    ),
    (
        ["buy", "should i", "entry", "eth", "ethereum"],
        "ETH's range is tightening ⚖️ "
        "Upcoming network activity could act as a catalyst for a move. "
        "Consider a small position with a stop below the recent swing low.",
    ),
    (
        ["buy", "should i", "entry", "sol", "solana"],
        "SOL has strong developer traction and fast throughput ⚡ "
        "Watch congestion events — they've historically hit price hard. "
        "Support near recent lows is the key level to defend.",
    ),
    (
        ["buy", "should i", "entry", "xrp", "ripple"],
        "XRP is driven more by legal developments than technicals right now ⚖️ "
        "Regulatory clarity could move the price ±30% in a day. "
        "Data unclear 🤷 — position sizing should reflect that binary risk.",
    ),
    (
        ["sell", "exit", "dump", "take profit"],
        "Selling into strength is smart if you're significantly up 📉 "
        "Always keep a portion to avoid missing extended runs. "
        "Trim gradually rather than exiting all at once.",
    ),
    (
        ["bear", "crash", "drop", "down", "correction"],
        "Corrections are healthy in any bull cycle 🐻 "
        "The key question is whether key weekly-close support levels hold. "
        "Data unclear 🤷 — short-term direction needs more confirmation before sizing a short.",
    ),
    (
        ["bull", "moon", "pump", "rally", "all time high", "ath"],
        "Bullish momentum exists on higher timeframes 🚀 "
        "But chasing parabolic moves carries maximum drawdown risk. "
        "Look for consolidation patterns or retest of breakout levels before adding.",
    ),
    (
        ["defi", "yield", "farm", "liquidity", "stake", "staking"],
        "DeFi yields have compressed significantly since 2021 📉 "
        "Sustainable APYs on blue-chip protocols are now 5–15%. "
        "Always audit smart contract risk and understand impermanent loss before deploying.",
    ),
    (
        ["nft", "jpeg", "collectible", "opensea"],
        "NFT market volume is a fraction of its 2022 peak 🎨 "
        "Liquidity is thin — exits can be very difficult when sentiment turns. "
        "Treat NFTs as speculative collectibles, not liquid investments.",
    ),
    (
        ["macro", "fed", "rate", "inflation", "recession"],
        "Crypto remains highly correlated with risk-on macro sentiment 📊 "
        "Fed rate decisions and CPI prints move BTC almost as much as altcoins. "
        "Watch DXY and 10Y yields — when they drop, crypto historically rallies.",
    ),
    (
        ["altcoin", "alt", "season", "small cap", "gem"],
        "Altcoin seasons typically follow BTC dominance breaking down from highs 🔄 "
        "ETH leads, then large caps, then mids, then small caps — in that order. "
        "Liquidity thins fast in small caps — size positions accordingly.",
    ),
    (
        ["rsi", "macd", "indicator", "technical", "chart"],
        "RSI above 70 = overbought caution, below 30 = oversold opportunity 📈 "
        "MACD bullish crossover + RSI recovering from oversold is a strong combo. "
        "Use /signal BTC for live computed indicators on any coin.",
    ),
]

_DEFAULT_MOCK = (
    "Crypto markets are driven by macro sentiment, on-chain flows, and momentum 📊 "
    "Without real-time AI access I can't give a precise call on that right now. "
    "Data unclear 🤷 — set OPENAI_API_KEY in .env for live AI-powered answers."
)


# ── Public API ────────────────────────────────────────────────────────────────

async def ask_ai(uid: int, question: str) -> str:
    """
    Process a user question with conversation context and return a formatted reply.

    Args:
        uid:      Telegram user ID (used to key per-user history).
        question: Raw user message text.

    Returns:
        HTML-formatted Telegram message string.
    """
    question = question.strip()
    if not question:
        return "❓ <b>Please type a question.</b>"

    conv = get_conversation(uid)
    history = conv.to_messages()

    logger.info(
        "AI request uid=%s turns_in_context=%d question=%.60s",
        uid, conv.length, question,
    )

    # ── Get answer ────────────────────────────────────────────────────────────
    if settings.OPENAI_API_KEY:
        raw_answer = await _call_openai(question, history)
    else:
        raw_answer = _smart_mock(question)

    # ── Persist this turn ─────────────────────────────────────────────────────
    conv.add(user_text=question, assistant_text=raw_answer)

    logger.info("AI response uid=%s turns_now=%d", uid, conv.length)

    return _format_reply(raw=raw_answer, turns=conv.length)


def clear_chat(uid: int) -> None:
    """Clear conversation history for a user. Called by the 🗑 Clear button."""
    clear_conversation(uid)
    logger.info("Cleared conversation for uid=%s", uid)


def get_chat_context_info(uid: int) -> dict:
    """
    Return context metadata for displaying in the UI.

    Returns:
        {
            "turns":    int,   # 0-MAX_TURNS
            "max":      int,   # MAX_TURNS
            "has_hist": bool,
            "dots":     str,   # e.g. "●●●○○"
        }
    """
    turns = conversation_length(uid)
    return {
        "turns":    turns,
        "max":      MAX_TURNS,
        "has_hist": has_conversation(uid),
        "dots":     _memory_dots(turns),
    }


# ── OpenAI call ───────────────────────────────────────────────────────────────

async def _call_openai(question: str, history: list[dict]) -> str:
    """
    Build the full message array and call OpenAI gpt-4o-mini.

    Message order: system → history (oldest first) → new question
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model":       OPENAI_MODEL,
        "messages":    messages,
        "max_tokens":  MAX_TOKENS,
        "temperature": TEMPERATURE,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENAI_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status == 401:
                    logger.error("OpenAI 401 — invalid key")
                    return "⚠️ API key rejected. Contact the bot admin."
                if resp.status == 429:
                    logger.warning("OpenAI rate-limited")
                    return "⏳ AI is busy right now. Try again in a moment."
                if resp.status != 200:
                    body = await resp.text()
                    raise ValueError(f"OpenAI HTTP {resp.status}: {body[:120]}")
                data = await resp.json()

        return data["choices"][0]["message"]["content"].strip()

    except aiohttp.ClientError as exc:
        logger.error("Network error → OpenAI: %s", exc)
        return "Data unclear 🤷 — network error reaching AI. Please try again."
    except Exception as exc:
        logger.error("Unexpected OpenAI error: %s", exc)
        return "Data unclear 🤷 — unexpected error. Please try again."


# ── Smart mock ────────────────────────────────────────────────────────────────

def _smart_mock(question: str) -> str:
    """
    Keyword-matched demo responses used when OPENAI_API_KEY is not set.
    Returns the best match, or the default response.
    """
    q = question.lower()
    best: tuple[int, str] = (0, _DEFAULT_MOCK)

    for keywords, response in _MOCK_RULES:
        hits = sum(1 for kw in keywords if kw in q)
        if hits > best[0]:
            best = (hits, response)

    return best[1]


# ── Formatting ────────────────────────────────────────────────────────────────

def _format_reply(raw: str, turns: int) -> str:
    """
    Wrap the raw AI answer in a Telegram HTML card.

    Layout:
      💬 FutureGPT AI
      ━━━━━━━━━━━━━━━━━━━━
      <answer text>
      ━━━━━━━━━━━━━━━━━━━━
      Memory ●●●○○  ·  Not financial advice
    """
    safe = _escape_html(raw)
    dots = _memory_dots(turns)

    return (
        f"💬 <b>FutureGPT AI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{safe}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Memory {dots}  ·  Not financial advice</i>"
    )


def _memory_dots(turns: int, max_t: int = MAX_TURNS) -> str:
    """Visual memory indicator: ●●●○○ = 3 of 5 turns stored."""
    filled = min(turns, max_t)
    return "●" * filled + "○" * (max_t - filled)


def _escape_html(text: str) -> str:
    """
    Minimal HTML sanitisation for Telegram's HTML mode.
    Escapes bare & < > that aren't already part of allowed tags.
    Preserves <b>, <i>, <code>, <pre>, <a>, <s>, <u>.
    """
    # Escape bare ampersands not already an HTML entity
    text = re.sub(r'&(?!amp;|lt;|gt;|quot;|#\d+;)', '&amp;', text)
    # Escape < that aren't opening a known safe tag
    text = re.sub(
        r'<(?!/?(?:b|i|code|pre|a|s|u|em|strong)\b)',
        '&lt;',
        text,
    )
    return text
