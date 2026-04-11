# 📊 Crypto Market Analyst Bot

A full-featured Telegram crypto analysis bot. Pulls data from **Binance** (Bybit fallback), analyzes 1H + 4H timeframes, and fires smart alerts to your Telegram.

---

## 🧠 Analysis Modules

| Module | What it does |
|---|---|
| **Support & Resistance** | Pivot-based levels with touch count & strength rating |
| **Market Structure** | HH / HL / LH / LL sequence + BOS / CHoCH detection |
| **Candlestick Patterns** | 15+ patterns: Engulfing, Morning Star, Doji, Marubozu, etc. |
| **Liquidity Zones** | Equal highs/lows, buy/sell-side pools, stop hunt detection |
| **Volume Analysis** | Rising/falling trend, spike detection, climax candle |
| **RSI** | Zones, direction, overbought/oversold |
| **MACD** | Crossover detection, momentum, histogram trend |
| **EMA Filter** | EMA 21/55/200 trend + Golden/Death cross |
| **RSI Divergence** | Regular & Hidden bullish/bearish divergence |
| **MACD Divergence** | Regular bullish/bearish divergence |
| **Fibonacci** | Retracement + extension levels, golden zone detection |
| **Confluence Score** | All signals aggregated → -10 to +10 bias score |

---

## 📱 Telegram Commands

| Command | Description |
|---|---|
| `/analyze BTC` | Full analysis — all 12 modules, 1H + 4H |
| `/summary BTC` | Quick bias snapshot with confluence score bar |
| `/support ETH` | Support & Resistance levels only |
| `/patterns SOL` | Candlestick patterns only |
| `/liquidity BNB` | Liquidity zones + stop hunt zones |
| `/fib BTC` | Fibonacci retracement & extension targets |
| `/scan` | Scan top 20 coins, ranked by confluence score |
| `/scan ETH SOL ARB` | Scan a custom coin list |
| `/alert add BTC` | Add BTC to watchlist |
| `/alert remove BTC` | Remove from watchlist |
| `/alert list` | View current watchlist |

---

## 🔔 Smart Alert System

The background loop (every 5 min) fires a Telegram alert when:
- ✅ Bullish/bearish candlestick pattern detected
- 🏗 Break of Structure (BOS) or Change of Character (CHoCH)
- ⚡ Stop hunt spotted on the chart
- 🔀 RSI or MACD divergence found
- 📐 Price entered Fibonacci golden zone

---

## 📁 Project Structure

```
crypto_bot/
├── bot.py                     ← Telegram bot, all commands + alert loop
├── analyzer.py                ← Master orchestrator
├── data_fetcher.py            ← CCXT: Binance + Bybit
├── formatter.py               ← All Telegram message formatters
├── scanner.py                 ← Multi-coin parallel scanner
├── watchlist.py               ← Alert watchlist (JSON-backed)
├── config.py                  ← All settings
├── requirements.txt
├── .env                       ← Your secrets (not in git)
└── analysis/
    ├── support_resistance.py
    ├── market_structure.py
    ├── candlestick_patterns.py
    ├── indicators.py           ← RSI, MACD, EMA, Volume
    ├── liquidity.py
    ├── fibonacci.py
    ├── divergence.py
    └── confluence.py           ← Confluence scoring engine
```

---

## ⚙️ Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create your `.env` file
```bash
cp .env.example .env
```

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=your_token_from_botfather
TELEGRAM_CHAT_ID=your_chat_id_here
```

> **Get Bot Token:** Message [@BotFather](https://t.me/BotFather) → `/newbot`  
> **Get Chat ID:** Message [@userinfobot](https://t.me/userinfobot)

Binance/Bybit API keys are optional — public OHLCV data requires no authentication.

### 3. Run
```bash
python bot.py
```

---

## ⚙️ config.py Settings

| Setting | Default | Description |
|---|---|---|
| `TIMEFRAMES` | `["1h", "4h"]` | Timeframes to analyze |
| `CANDLE_LIMIT` | `200` | Candles per request |
| `SR_LOOKBACK` | `50` | Candles used for S/R detection |
| `ALERT_CHECK_INTERVAL` | `300` | Watchlist check every 5 min |
| `EMA_FAST/SLOW/TREND` | `21/55/200` | EMA periods |
| `RSI_PERIOD` | `14` | RSI period |

---

## 📌 Notes

- Binance is tried first; Bybit is the automatic fallback.
- `/scan` uses 6 parallel threads — usually completes in 30–60s.
- Watchlist is saved to `watchlist.json` (persists across restarts).
- All formatters handle Telegram's 4096-char limit automatically.
