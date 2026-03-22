# 🚀 CoinGPT Bot — AI Crypto Assistant for Telegram

A production-ready Telegram bot built with **Python + aiogram 3** that delivers live crypto prices, trading signals, news, and AI-powered Q&A — all from a clean inline keyboard interface.

---

## 📁 Project Structure

```
coingpt_bot/
├── main.py                  # Entry point — bootstraps bot & dispatcher
├── config.py                # Centralised settings from env vars
├── requirements.txt
├── .env.example             # Copy to .env and fill in your keys
├── Dockerfile
├── docker-compose.yml
│
├── handlers/
│   ├── __init__.py
│   ├── commands.py          # /start /help /price /signal /news
│   └── callbacks.py        # Inline button handlers + FSM for Ask AI
│
├── keyboards/
│   ├── __init__.py
│   └── main_keyboard.py     # Inline keyboard factory functions
│
├── services/
│   ├── __init__.py
│   ├── crypto_service.py    # Live prices via CoinGecko API
│   ├── signal_service.py    # Trading signal engine (pluggable)
│   ├── news_service.py      # Crypto news via CryptoPanic API
│   └── ai_service.py        # GPT-4o AI Q&A via OpenAI API
│
└── utils/
    ├── __init__.py
    └── logger.py            # Structured console logging setup
```

---

## ⚡ Quick Start

### 1. Clone & install

```bash
git clone https://github.com/yourname/coingpt-bot.git
cd coingpt-bot
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set BOT_TOKEN
```

### 3. Run

```bash
python main.py
```

---

## 🐳 Docker

```bash
# Build & start
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 🔑 Environment Variables

| Variable            | Required | Description                                      |
|---------------------|----------|--------------------------------------------------|
| `BOT_TOKEN`         | ✅ Yes   | Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `LOG_LEVEL`         | No       | `DEBUG` / `INFO` / `WARNING` (default: `INFO`)   |
| `NEWS_API_KEY`      | No       | [CryptoPanic](https://cryptopanic.com/developers/api/) API key for live news |
| `OPENAI_API_KEY`    | No       | [OpenAI](https://platform.openai.com/api-keys) key for real GPT answers |

> Without optional keys the bot runs in **demo mode** with realistic mock data.

---

## 🤖 Features

| Feature | Trigger | Description |
|---------|---------|-------------|
| **Welcome** | `/start` | Greeting + inline menu |
| **Prices** | `📊 Price` button / `/price` | Top-5 coin prices via CoinGecko |
| **Signals** | `📈 Signal` button / `/signal` | Buy/Sell/Hold signals with reasoning |
| **News** | `📰 News` button / `/news` | Hot crypto headlines via CryptoPanic |
| **Ask AI** | `💬 Ask AI` button | FSM conversation flow → GPT-4o answer |
| **Help** | `/help` | Command reference |

---

## 🏗 Extending the Bot

### Add a new command
1. Create a handler function in `handlers/commands.py` decorated with `@router.message(Command("mycommand"))`
2. Add a new service in `services/` if it needs external data
3. Register the router in `main.py` (already done for the commands router)

### Add a new inline button
1. Add a new `InlineKeyboardButton` in `keyboards/main_keyboard.py` with a unique `callback_data`
2. Add a matching `@router.callback_query(F.data == "action:myaction")` handler in `handlers/callbacks.py`

### Plug in real trading signals
Replace the mock data in `services/signal_service.py` with calls to `pandas-ta` or `ta-lib`:
```python
import pandas_ta as ta
# df.ta.rsi(), df.ta.macd(), etc.
```

---

## 🛡 Production Tips

- Use **webhook mode** instead of polling for high-traffic bots (`aiogram` supports it natively)
- Store FSM state in **Redis** (`aiogram.fsm.storage.redis.RedisStorage`) instead of memory
- Add **rate limiting** middleware to prevent abuse
- Use **PostgreSQL** to persist user data and conversation history
- Set up **health-check** endpoint for container orchestration

---

## 📄 License

MIT — free to use, modify, and distribute.
