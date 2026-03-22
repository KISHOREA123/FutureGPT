"""
handlers/chat_handler.py — AI chat interactions.

CHAT HISTORY FIX:
  The previous version edited a single placeholder message for every answer.
  This made every response overwrite the previous one — no visible history.

  Fix: each answer is sent as a NEW message. The "thinking..." spinner is
  also a new message, which is then edited to the answer. This way the full
  conversation is visible as a normal message thread in Telegram.

  Quick-question buttons also now send a new message rather than editing
  the prompt card, preserving the prompt on screen above the conversation.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.chat_keyboard import (
    chat_prompt_keyboard,
    chat_reply_keyboard,
    chat_clear_confirm_keyboard,
)
from services.ai_service import ask_ai, clear_chat, get_chat_context_info

logger = logging.getLogger(__name__)
router = Router(name="chat")


# ── FSM ───────────────────────────────────────────────────────────────────────

class AskAIStates(StatesGroup):
    waiting_for_question = State()


# ── Screen text ───────────────────────────────────────────────────────────────

def _prompt_text(uid: int) -> str:
    ctx  = get_chat_context_info(uid)
    dots = ctx["dots"]
    mem  = (
        f"<i>Memory: {dots}  ({ctx['turns']}/{ctx['max']} turns)</i>"
        if ctx["has_hist"]
        else "<i>Start by typing a question below.</i>"
    )
    return (
        "💬 <b>FutureGPT AI</b>  —  Crypto Chat\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "  📊 Price outlook on any coin\n"
        "  📈 Signal interpretation\n"
        "  🧠 DeFi, NFTs, L2s, concepts\n"
        "  ⚖️ Risk / position sizing\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{mem}\n"
        "⌨️ <i>Type your question or tap a shortcut ↓</i>"
    )

_THINKING = (
    "🤔 <b>FutureGPT AI is thinking…</b>\n\n"
    "<i>Analysing with market context</i>\n\n"
    "<code>▓▓▓▓▓▓▓░░░  70%</code>"
)


# ── Enter chat ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "action:askai")
async def cb_enter_chat(query: CallbackQuery, state: FSMContext) -> None:
    await query.answer()
    uid = query.from_user.id
    await state.set_state(AskAIStates.waiting_for_question)
    ctx  = get_chat_context_info(uid)
    text = _prompt_text(uid)
    # Edit the current message to the prompt screen
    try:
        await query.message.edit_text(
            text, reply_markup=chat_prompt_keyboard(has_history=ctx["has_hist"])
        )
    except Exception:
        await query.message.answer(
            text, reply_markup=chat_prompt_keyboard(has_history=ctx["has_hist"])
        )


# ── Quick-question buttons ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("ai:q:"))
async def cb_quick_question(query: CallbackQuery, state: FSMContext) -> None:
    question = query.data[5:]
    uid      = query.from_user.id
    await query.answer(f"💬 {question[:30]}…")

    # Send thinking as a NEW message — preserves the prompt card above
    thinking_msg = await query.message.answer(_THINKING)
    await _answer_and_edit(thinking_msg, state, uid, question)


# ── Free-text message ─────────────────────────────────────────────────────────

@router.message(AskAIStates.waiting_for_question)
async def msg_question(message: Message, state: FSMContext) -> None:
    question = (message.text or "").strip()
    uid      = message.from_user.id

    if not question:
        await message.answer("❓ Please type a question.")
        return

    logger.info("User %s: %.80s", uid, question)

    # Send thinking as a new message, then edit it to the answer
    thinking_msg = await message.answer(_THINKING)
    await _answer_and_edit(thinking_msg, state, uid, question)


# ── Clear history ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "ai:clear")
async def cb_clear_request(query: CallbackQuery) -> None:
    await query.answer()
    try:
        await query.message.edit_text(
            "🗑 <b>Clear conversation history?</b>\n\n"
            "<i>FutureGPT will lose memory of this session.</i>",
            reply_markup=chat_clear_confirm_keyboard(),
        )
    except Exception:
        await query.message.answer(
            "🗑 <b>Clear conversation history?</b>",
            reply_markup=chat_clear_confirm_keyboard(),
        )


@router.callback_query(F.data == "ai:clear:confirm")
async def cb_clear_confirm(query: CallbackQuery, state: FSMContext) -> None:
    uid = query.from_user.id
    clear_chat(uid)
    await query.answer("🗑 History cleared!")
    await state.set_state(AskAIStates.waiting_for_question)
    text = _prompt_text(uid)
    try:
        await query.message.edit_text(
            text, reply_markup=chat_prompt_keyboard(has_history=False)
        )
    except Exception:
        await query.message.answer(
            text, reply_markup=chat_prompt_keyboard(has_history=False)
        )


# ── Core AI runner ────────────────────────────────────────────────────────────

async def _answer_and_edit(
    thinking_msg: Message,
    state: FSMContext,
    uid: int,
    question: str,
) -> None:
    """
    Call AI, then EDIT the thinking message to the answer.
    Because thinking_msg is always a fresh message, each answer
    appears as a new bubble in the chat — full history is visible.
    """
    try:
        answer = await ask_ai(uid, question)
        ctx    = get_chat_context_info(uid)
        await thinking_msg.edit_text(
            answer,
            reply_markup=chat_reply_keyboard(has_history=ctx["has_hist"]),
            disable_web_page_preview=True,
        )
    except Exception as exc:
        logger.error("AI error uid=%s: %s", uid, exc)
        await thinking_msg.edit_text(
            "⚠️ <b>AI Unavailable</b>\n\n"
            "<i>Could not get a response. Please try again.</i>",
            reply_markup=chat_reply_keyboard(has_history=False),
        )

    # Keep FSM active — user can type the next question immediately
    await state.set_state(AskAIStates.waiting_for_question)