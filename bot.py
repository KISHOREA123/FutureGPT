import asyncio
import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ALERT_CHECK_INTERVAL
from analyzer import run_full_analysis
from formatter import (
    format_full_analysis,
    format_sr_only,
    format_patterns_only,
    format_liquidity_only,
    format_summary,
    format_scan_results,
    format_fib_only,
    format_ob_fvg_only,
    format_volatility_only,
    format_report,
    format_trade_setup,
    format_grade_only,
)
from scanner import run_scan, DEFAULT_SCAN_LIST
from watchlist import (
    add_to_watchlist,
    remove_from_watchlist,
    list_watchlist,
    get_watchlist_symbols,
    update_last_alert,
)
from keyboard_ui import (
    build_coins_keyboard,
    build_coin_action_keyboard,
    build_timeframe_keyboard,
    timeframe_header,
    coins_page_header,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def parse_coin(args: list) -> str | None:
    if not args:
        return None
    return args[0].upper().replace("/USDT", "").strip()


async def send_chunks(update_or_query, text: str, reply_markup=None):
    """
    Split long messages and send in chunks.
    Works with both Update (command) and CallbackQuery (button tap).
    """
    MAX = 4000
    chunks = [text[i : i + MAX] for i in range(0, len(text), MAX)]
    is_query = hasattr(update_or_query, "message") and hasattr(update_or_query, "answer")

    for idx, chunk in enumerate(chunks):
        # Only attach keyboard to last chunk
        markup = reply_markup if idx == len(chunks) - 1 else None
        if is_query:
            await update_or_query.message.reply_text(
                chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=markup
            )
        else:
            await update_or_query.message.reply_text(
                chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=markup
            )


async def do_full_analysis(coin: str, send_fn, reply_markup=None):
    """
    Shared analysis runner — used by both command handlers and callback handlers.
    send_fn is an async callable that accepts (text, reply_markup).
    """
    results = run_full_analysis(coin)
    msg     = format_full_analysis(results)
    MAX     = 4000
    chunks  = [msg[i : i + MAX] for i in range(0, len(msg), MAX)]
    for idx, chunk in enumerate(chunks):
        markup = reply_markup if idx == len(chunks) - 1 else None
        await send_fn(chunk, markup)


# ─────────────────────────────────────────────
# /start  /help
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 *Crypto Market Analyst Bot*\n\n"
        "🪙 *Browse Coins:*\n"
        "`/coins` — Open coin browser \\(100 coins, tap to analyze\\)\n\n"
        "📊 *Analysis Commands:*\n"
        "`/analyze BTC` — Full analysis \\(all modules\\)\n"
        "`/report BTC` — Complete chart report \\(institutional grade\\)\n"
        "`/summary BTC` — Quick bias \\+ confluence score\n"
        "`/support BTC` — Support \& Resistance\n"
        "`/patterns BTC` — Candlestick patterns\n"
        "`/liquidity BTC` — Liquidity zones \& stop hunts\n"
        "`/fib BTC` — Fibonacci levels\n"
        "`/ob BTC` — Order Blocks \& Fair Value Gaps\n"
        "`/volatility BTC` — ATR \\+ Bollinger Bands\n\n"
        "🎯 *Trade Quality:*\n"
        "`/trade BTC` — Trade setup with Entry/SL/TP\n"
        "`/grade BTC` — Signal quality grade \\(A\\+ to F\\)\n\n"
        "🔍 *Scanner:*\n"
        "`/scan` — Scan top 20 coins by confluence\n"
        "`/scan ETH SOL BNB` — Custom list\n\n"
        "🔔 *Alerts:*\n"
        "`/alert add BTC` · `/alert remove BTC` · `/alert list`\n\n"
        "_Tip: Use /coins for the fastest way to analyze any coin\\._"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)


# ─────────────────────────────────────────────
# /coins — Coin Browser Keyboard
# ─────────────────────────────────────────────

async def cmd_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page   = 1
    header = coins_page_header(page)
    kb     = build_coins_keyboard(page)
    await update.message.reply_text(header, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


# ─────────────────────────────────────────────
# /analyze
# ─────────────────────────────────────────────

async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = parse_coin(context.args)
    if not coin:
        await update.message.reply_text(
            "❌ Usage: `/analyze <coin>`\nOr use /coins to browse.", parse_mode=ParseMode.MARKDOWN
        )
        return
    await update.message.reply_text(f"⏳ Analyzing *{coin}*...", parse_mode=ParseMode.MARKDOWN)
    try:
        action_kb = build_coin_action_keyboard(coin)
        async def send_fn(text, markup):
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        await do_full_analysis(coin, send_fn, reply_markup=action_kb)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─────────────────────────────────────────────
# /summary
# ─────────────────────────────────────────────

async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin = parse_coin(context.args)
    if not coin:
        await update.message.reply_text("❌ Usage: `/summary <coin>`", parse_mode=ParseMode.MARKDOWN)
        return
    await update.message.reply_text(f"⏳ Getting summary for *{coin}*...", parse_mode=ParseMode.MARKDOWN)
    try:
        results = run_full_analysis(coin)
        action_kb = build_coin_action_keyboard(coin)
        await send_chunks(update, format_summary(results), reply_markup=action_kb)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ─────────────────────────────────────────────
# /support /patterns /liquidity /fib /ob /volatility
# ─────────────────────────────────────────────

async def _sub_analysis(update, coin, label, formatter_fn):
    await update.message.reply_text(f"⏳ {label} for *{coin}*...", parse_mode=ParseMode.MARKDOWN)
    try:
        results  = run_full_analysis(coin)
        action_kb = build_coin_action_keyboard(coin)
        await send_chunks(update, formatter_fn(results), reply_markup=action_kb)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cmd_support(update, context):
    coin = parse_coin(context.args)
    if not coin: await update.message.reply_text("❌ Usage: `/support <coin>`", parse_mode=ParseMode.MARKDOWN); return
    await _sub_analysis(update, coin, "Fetching S/R levels", format_sr_only)

async def cmd_patterns(update, context):
    coin = parse_coin(context.args)
    if not coin: await update.message.reply_text("❌ Usage: `/patterns <coin>`", parse_mode=ParseMode.MARKDOWN); return
    await _sub_analysis(update, coin, "Detecting patterns", format_patterns_only)

async def cmd_liquidity(update, context):
    coin = parse_coin(context.args)
    if not coin: await update.message.reply_text("❌ Usage: `/liquidity <coin>`", parse_mode=ParseMode.MARKDOWN); return
    await _sub_analysis(update, coin, "Mapping liquidity", format_liquidity_only)

async def cmd_fib(update, context):
    coin = parse_coin(context.args)
    if not coin: await update.message.reply_text("❌ Usage: `/fib <coin>`", parse_mode=ParseMode.MARKDOWN); return
    await _sub_analysis(update, coin, "Calculating Fibonacci", format_fib_only)

async def cmd_ob(update, context):
    coin = parse_coin(context.args)
    if not coin: await update.message.reply_text("❌ Usage: `/ob <coin>`", parse_mode=ParseMode.MARKDOWN); return
    await _sub_analysis(update, coin, "Detecting OB & FVG", format_ob_fvg_only)

async def cmd_volatility(update, context):
    coin = parse_coin(context.args)
    if not coin: await update.message.reply_text("❌ Usage: `/volatility <coin>`", parse_mode=ParseMode.MARKDOWN); return
    await _sub_analysis(update, coin, "Analyzing volatility", format_volatility_only)

async def cmd_report(update, context):
    coin = parse_coin(context.args)
    if not coin: await update.message.reply_text("❌ Usage: `/report <coin>`", parse_mode=ParseMode.MARKDOWN); return
    await _sub_analysis(update, coin, "Generating full report", format_report)

async def cmd_trade(update, context):
    coin = parse_coin(context.args)
    if not coin: await update.message.reply_text("❌ Usage: `/trade <coin>`", parse_mode=ParseMode.MARKDOWN); return
    await _sub_analysis(update, coin, "Building trade setup", format_trade_setup)

async def cmd_grade(update, context):
    coin = parse_coin(context.args)
    if not coin: await update.message.reply_text("❌ Usage: `/grade <coin>`", parse_mode=ParseMode.MARKDOWN); return
    await _sub_analysis(update, coin, "Checking signal grade", format_grade_only)


# ─────────────────────────────────────────────
# /scan
# ─────────────────────────────────────────────

async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    custom = [a.upper().replace("/USDT", "") for a in context.args] if context.args else None
    coin_list = custom or DEFAULT_SCAN_LIST
    await update.message.reply_text(
        f"🔍 Scanning *{len(coin_list)} coins*... (~30–60s) ⏳", parse_mode=ParseMode.MARKDOWN
    )
    try:
        loop = asyncio.get_event_loop()
        scan = await loop.run_in_executor(None, lambda: run_scan(coin_list))
        await send_chunks(update, format_scan_results(scan))
    except Exception as e:
        await update.message.reply_text(f"❌ Scan error: {e}")


# ─────────────────────────────────────────────
# /alert
# ─────────────────────────────────────────────

async def cmd_alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ Usage:\n`/alert add <coin>`\n`/alert remove <coin>`\n`/alert list`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    sub = args[0].lower()
    if sub == "list":
        await update.message.reply_text(list_watchlist(), parse_mode=ParseMode.MARKDOWN)
    elif sub == "add":
        if len(args) < 2:
            await update.message.reply_text("❌ Usage: `/alert add <coin>`", parse_mode=ParseMode.MARKDOWN); return
        await update.message.reply_text(add_to_watchlist(args[1]), parse_mode=ParseMode.MARKDOWN)
    elif sub == "remove":
        if len(args) < 2:
            await update.message.reply_text("❌ Usage: `/alert remove <coin>`", parse_mode=ParseMode.MARKDOWN); return
        await update.message.reply_text(remove_from_watchlist(args[1]), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("❌ Unknown subcommand. Use: add | remove | list")


# ─────────────────────────────────────────────
# UNKNOWN COMMAND
# ─────────────────────────────────────────────

async def cmd_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Unknown command. Type /start or use /coins to browse.")


# ─────────────────────────────────────────────
# CALLBACK QUERY HANDLER (all button taps)
# ─────────────────────────────────────────────

async def safe_answer(query, text: str = ""):
    """
    Answer the callback query IMMEDIATELY to beat Telegram's 10-second deadline.
    Must be called before any awaited network or analysis work.
    Silently ignores BadRequest if the query already expired.
    """
    try:
        await query.answer(text=text)
    except BadRequest:
        pass  # already timed out — nothing we can do


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data

    # ── No-op (placeholder buttons like page counter) ────────
    if data == "noop":
        await safe_answer(query)
        return

    # ── Page navigation: coins_page:<n> ──────────────────────
    if data.startswith("coins_page:"):
        await safe_answer(query)          # ← answer BEFORE any work
        page   = int(data.split(":")[1])
        header = coins_page_header(page)
        kb     = build_coins_keyboard(page)
        try:
            await query.edit_message_text(
                header, parse_mode=ParseMode.MARKDOWN, reply_markup=kb
            )
        except BadRequest:
            pass
        return

    # ── Close keyboard ────────────────────────────────────────
    if data == "close_kb":
        await safe_answer(query)          # ← answer BEFORE any work
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except BadRequest:
            pass
        return

    # ── Watch (add to alert watchlist) ───────────────────────
    if data.startswith("watch:"):
        coin = data.split(":")[1]
        await safe_answer(query, f"👀 Watching {coin}!")  # ← immediate toast
        msg = add_to_watchlist(coin)
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

    # ── Scan all ──────────────────────────────────────────────
    if data == "scan_all":
        await safe_answer(query, "🔍 Starting scan...")   # ← immediate toast
        await query.message.reply_text(
            f"🔍 Scanning *{len(DEFAULT_SCAN_LIST)} coins*... (~30-60s) ⏳",
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            loop = asyncio.get_event_loop()
            scan = await loop.run_in_executor(None, lambda: run_scan(DEFAULT_SCAN_LIST))
            msg  = format_scan_results(scan)
            MAX  = 4000
            for chunk in [msg[i : i + MAX] for i in range(0, len(msg), MAX)]:
                await query.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await query.message.reply_text(f"❌ Scan error: {e}")
        return

    # ── Select coin (from coins keyboard) ────────────────────
    if data.startswith("select_coin:"):
        coin = data.split(":")[1]
        await safe_answer(query)
        action_kb = build_coin_action_keyboard(coin)
        msg = f"🪙 *{coin}* selected.\n\nChoose an analysis option below:"
        try:
            await query.edit_message_text(
                msg, parse_mode=ParseMode.MARKDOWN, reply_markup=action_kb
            )
        except BadRequest:
            pass
        return

    # ── Pick analysis type → show timeframe keyboard ─────────
    if data.startswith("pick:"):
        parts = data.split(":")
        analysis_type = parts[1]
        coin = parts[2]
        await safe_answer(query)
        tf_kb = build_timeframe_keyboard(coin, analysis_type)
        header = timeframe_header(coin, analysis_type)
        try:
            await query.edit_message_text(
                header, parse_mode=ParseMode.MARKDOWN, reply_markup=tf_kb
            )
        except BadRequest:
            pass
        return

    # ── Run analysis on selected timeframe ────────────────────
    if data.startswith("tf:"):
        parts = data.split(":")
        analysis_type = parts[1]
        coin = parts[2]
        tf_choice = parts[3]

        if tf_choice == "all":
            tf_list = ["15m", "1h", "4h", "1d"]
            tf_label = "All Timeframes"
        else:
            tf_list = [tf_choice]
            tf_label = tf_choice.upper()

        formatter_map = {
            "analyze":    ("📊 Full Analysis",    format_full_analysis),
            "support":    ("📍 S/R",              format_sr_only),
            "patterns":   ("🕯 Patterns",         format_patterns_only),
            "liquidity":  ("💧 Liquidity",        format_liquidity_only),
            "fib":        ("📐 Fibonacci",         format_fib_only),
            "ob":         ("🧱 OB & FVG",          format_ob_fvg_only),
            "volatility": ("📏 Volatility",        format_volatility_only),
            "report":     ("📋 Report",            format_report),
            "trade":      ("🎯 Trade Setup",       format_trade_setup),
            "grade":      ("🏆 Grade",             format_grade_only),
            "summary":    ("📑 Summary",           format_summary),
        }

        label, formatter = formatter_map.get(
            analysis_type,
            ("📊 Analysis", format_full_analysis),
        )

        await safe_answer(query, f"⏳ {label}...")
        await query.message.reply_text(
            f"⏳ {label} for *{coin}* `{tf_label}`...",
            parse_mode=ParseMode.MARKDOWN,
        )

        try:
            loop      = asyncio.get_event_loop()
            results   = await loop.run_in_executor(
                None, lambda: run_full_analysis(coin, timeframes=tf_list)
            )
            action_kb = build_coin_action_keyboard(coin)
            msg       = formatter(results)
            MAX       = 4000
            chunks    = [msg[i : i + MAX] for i in range(0, len(msg), MAX)]
            for idx, chunk in enumerate(chunks):
                markup = action_kb if idx == len(chunks) - 1 else None
                await query.message.reply_text(
                    chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=markup
                )
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {e}")
        return



# ─────────────────────────────────────────────
# BACKGROUND WATCHLIST ALERT LOOP
# ─────────────────────────────────────────────

async def watchlist_alert_loop(app: Application):
    await asyncio.sleep(45)
    logger.info("📡 Watchlist alert loop started.")

    while True:
        symbols = get_watchlist_symbols()
        chat_id = app.bot_data.get("alert_chat_id")

        for sym in symbols:
            try:
                results     = run_full_analysis(sym)
                alert_blocks = []

                for tf, data in results.items():
                    if tf == "__htf__" or "error" in data:
                        continue

                    triggers = []

                    for p in data.get("candlestick_patterns", []):
                        if p["type"] in ("bullish", "bearish"):
                            e = "🟢" if p["type"] == "bullish" else "🔴"
                            triggers.append(f"{e} Pattern: *{p['pattern']}*")

                    bos = data.get("market_structure", {}).get("bos_choch", "None")
                    if bos != "None":
                        triggers.append(f"🏗 {bos}")

                    for h in data.get("liquidity", {}).get("stop_hunts", [])[-1:]:
                        triggers.append(f"⚡ Stop Hunt: {h['type']} @ {h['price']}")

                    all_divs = (
                        data.get("divergence", {}).get("rsi", {}).get("divergences", []) +
                        data.get("divergence", {}).get("macd", {}).get("divergences", [])
                    )
                    for d in all_divs:
                        triggers.append(f"🔀 {d['type']}")

                    if data.get("fibonacci", {}).get("golden_zone"):
                        triggers.append("📐 At Fibonacci Golden Zone!")

                    bb = data.get("bollinger", {})
                    if "Squeeze" in bb.get("squeeze", ""):
                        triggers.append(f"📊 {bb['squeeze']}")

                    ob = data.get("order_blocks", {})
                    if ob.get("at_ob"):
                        triggers.append(f"🧱 {ob['at_ob']}")

                    fvg = data.get("fvg", {})
                    if fvg.get("at_fvg"):
                        triggers.append(f"📭 Price inside FVG: {fvg['at_fvg']}")

                    if triggers:
                        conf  = data.get("confluence", {})
                        price = data["current_price"]
                        p_fmt = f"${price:,.4f}" if price < 1000 else f"${price:,.2f}"
                        alert_blocks.append(
                            f"*{sym}/USDT* | _{tf}_ | {p_fmt}\n"
                            f"⚡ Bias: {conf.get('bias','N/A')} ({conf.get('score',0):+d}/10)\n"
                            + "\n".join(triggers)
                        )

                if alert_blocks and chat_id:
                    action_kb = build_coin_action_keyboard(sym)
                    full_msg  = "🔔 *WATCHLIST ALERT*\n\n" + "\n\n─────\n".join(alert_blocks)
                    MAX       = 4000
                    chunks    = [full_msg[i : i + MAX] for i in range(0, len(full_msg), MAX)]
                    for idx, chunk in enumerate(chunks):
                        markup = action_kb if idx == len(chunks) - 1 else None
                        await app.bot.send_message(
                            chat_id=chat_id,
                            text=chunk,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=markup,
                        )
                    update_last_alert(sym)
                    logger.info(f"Alert sent for {sym}")

            except Exception as e:
                logger.error(f"Alert loop error [{sym}]: {e}")

        await asyncio.sleep(ALERT_CHECK_INTERVAL)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("❌ TELEGRAM_BOT_TOKEN not set in .env!")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.bot_data["alert_chat_id"] = TELEGRAM_CHAT_ID

    # ── Command handlers ──────────────────────────────────────
    commands = [
        ("start",      cmd_start),
        ("help",       cmd_start),
        ("coins",      cmd_coins),
        ("analyze",    cmd_analyze),
        ("summary",    cmd_summary),
        ("support",    cmd_support),
        ("patterns",   cmd_patterns),
        ("liquidity",  cmd_liquidity),
        ("fib",        cmd_fib),
        ("ob",         cmd_ob),
        ("volatility", cmd_volatility),
        ("report",     cmd_report),
        ("trade",      cmd_trade),
        ("grade",      cmd_grade),
        ("scan",       cmd_scan),
        ("alert",      cmd_alert),
    ]
    for name, fn in commands:
        app.add_handler(CommandHandler(name, fn))

    # ── Inline keyboard callback handler ──────────────────────
    app.add_handler(CallbackQueryHandler(handle_callback))

    # ── Fallback for unknown commands ─────────────────────────
    app.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))

    async def post_init(app: Application):
        await app.bot.set_my_commands([
            BotCommand("coins",      "Browse 100 coins with keyboard"),
            BotCommand("analyze",    "Full market analysis"),
            BotCommand("report",     "Complete chart analysis report"),
            BotCommand("trade",      "Trade setup with entry/SL/TP"),
            BotCommand("grade",      "Signal quality grade (A+ to F)"),
            BotCommand("summary",    "Quick bias + confluence score"),
            BotCommand("scan",       "Scan & rank top coins"),
            BotCommand("support",    "Support & Resistance levels"),
            BotCommand("patterns",   "Candlestick patterns"),
            BotCommand("liquidity",  "Liquidity zones & stop hunts"),
            BotCommand("fib",        "Fibonacci retracement & targets"),
            BotCommand("ob",         "Order Blocks & Fair Value Gaps"),
            BotCommand("volatility", "ATR + Bollinger Bands"),
            BotCommand("alert",      "Watchlist alerts (add/remove/list)"),
            BotCommand("start",      "Show all commands"),
        ])
        asyncio.create_task(watchlist_alert_loop(app))
        logger.info("✅ Bot ready. All commands + keyboard UI registered.")

    app.post_init = post_init

    logger.info("🚀 Crypto Market Analyst Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
