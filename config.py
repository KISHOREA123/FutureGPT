import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Exchange settings
DEFAULT_EXCHANGE = "binance"   # "binance" or "bybit"
TIMEFRAMES = ["1h", "4h"]
CANDLE_LIMIT = 200             # How many candles to fetch per timeframe

# ── Data Fetching (retry / backoff) ──────────
API_MAX_RETRIES = 3
API_RETRY_DELAY = 2            # Initial delay in seconds
API_RETRY_BACKOFF = 2.0        # Exponential backoff multiplier

# Analysis settings
SR_LOOKBACK = 50               # Candles to look back for S/R levels
SR_TOUCH_TOLERANCE = 0.003     # 0.3% price tolerance for level touches
LIQUIDITY_EQUAL_TOLERANCE = 0.002  # 0.2% tolerance for equal highs/lows

# ── EMA periods ──────────────────────────────
EMA_SHORT = 9
EMA_MID = 21
EMA_FAST = 21
EMA_SLOW = 55
EMA_LONG = 50
EMA_TREND = 200

# ── RSI settings ─────────────────────────────
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# ── MACD settings ────────────────────────────
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# ── Stochastic ───────────────────────────────
STOCH_K_PERIOD = 14
STOCH_D_PERIOD = 3
STOCH_OVERBOUGHT = 80
STOCH_OVERSOLD = 20

# ── ADX / Trend Settings ────────────────────
ADX_PERIOD = 14
ADX_STRONG_TREND = 25          # ADX > 25 = strong trend
ADX_WEAK_TREND = 15            # ADX 15-25 = weak trend

# ── Bollinger Bands ──────────────────────────
BB_PERIOD = 20
BB_STD = 2.0

# ── ATR ──────────────────────────────────────
ATR_PERIOD = 14

# ── Ichimoku ─────────────────────────────────
ICHIMOKU_TENKAN = 9
ICHIMOKU_KIJUN = 26
ICHIMOKU_SENKOU_B = 52

# ── Supertrend ───────────────────────────────
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3.0

# ── Volume ───────────────────────────────────
VOLUME_MA_PERIOD = 20

# ── Fibonacci ────────────────────────────────
FIB_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]

# ── Watchlist alert check interval (seconds) ─
ALERT_CHECK_INTERVAL = 300   # 5 minutes

# ── Risk Management ─────────────────────────
DEFAULT_RISK_PCT = 2.0         # Risk 2% of account per trade
DEFAULT_ACCOUNT_SIZE = 1000    # Default account size in USD
DEFAULT_CAPITAL = 1000         # Alias for position sizing
DEFAULT_RISK_PER_TRADE = 2.0   # Alias for risk manager
MAX_LEVERAGE = 20              # Maximum leverage suggestion
MIN_RR_RATIO = 1.5             # Minimum Risk:Reward to consider tradeable
TP1_MULTIPLIER = 1.5           # TP1 = 1.5x risk distance
TP2_MULTIPLIER = 2.5           # TP2 = 2.5x risk distance
ATR_SL_MULTIPLIER = 1.5        # SL = 1.5x ATR from entry
MAX_DRAWDOWN_PERCENT = 15.0    # Max drawdown before circuit breaker

# ── Signal Quality Gate ──────────────────────
MIN_CONFLUENCE_SCORE = 3       # Minimum |score| to generate a trade setup
MIN_GRADE_TRADEABLE = "C+"     # Minimum grade to mark as tradeable
MIN_CONFIDENCE_PCT = 40        # Minimum confidence % to show trade
VOLUME_CONFIRMATION = True     # Require rising volume for trade setups

# ── ML Prediction ────────────────────────────
ML_ENABLED = True              # Run ML on every /analyze call
ML_LOOKAHEAD = 3               # Candles to predict ahead

# ── News Sentiment ───────────────────────────
NEWS_ENABLED = True            # Enable news sentiment (separate command)
NEWS_TIMEOUT = 10              # HTTP request timeout in seconds

# ── Order Flow / Whale Detection ─────────────
WHALE_VOLUME_CLIMAX_THRESHOLD = 3.0   # Volume must be Nx avg for climax
WHALE_ABSORPTION_THRESHOLD = 2.0
WHALE_EXHAUSTION_THRESHOLD = 2.0

# ── Correlation Filter ───────────────────────
CORRELATION_THRESHOLD = 0.80   # Above this = highly correlated

# ── Trading Sessions (UTC hours) ─────────────
TRADING_SESSIONS = {
    "asian": {
        "start": 0, "end": 8,
        "label": "🌏 Asian Session",
    },
    "london": {
        "start": 8, "end": 16,
        "label": "🇬🇧 London Session",
    },
    "new_york": {
        "start": 13, "end": 22,
        "label": "🇺🇸 New York Session",
    },
    "overlap_london_ny": {
        "start": 13, "end": 16,
        "label": "⚡ London/NY Overlap",
    },
}

SESSION_CONFIDENCE_ADJUST = {
    "asian": -3,
    "london": +3,
    "new_york": +2,
    "overlap_london_ny": +5,
    "off_hours": -5,
}

# ── Primary Timeframe ────────────────────────
PRIMARY_TIMEFRAME = "1h"

# ── Trading Pairs (fallback list) ────────────
TRADING_PAIRS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
    "DOGE/USDT", "ADA/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
]
