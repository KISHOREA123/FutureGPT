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

# Analysis settings
SR_LOOKBACK = 50               # Candles to look back for S/R levels
SR_TOUCH_TOLERANCE = 0.003     # 0.3% price tolerance for level touches
LIQUIDITY_EQUAL_TOLERANCE = 0.002  # 0.2% tolerance for equal highs/lows

# EMA periods
EMA_FAST = 21
EMA_SLOW = 55
EMA_TREND = 200

# RSI settings
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# MACD settings
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Watchlist alert check interval (in seconds)
ALERT_CHECK_INTERVAL = 300   # 5 minutes

# ── Risk Management ──────────────────────────────
DEFAULT_RISK_PCT = 2.0         # Risk 2% of account per trade
DEFAULT_ACCOUNT_SIZE = 1000    # Default account size in USD
MAX_LEVERAGE = 20              # Maximum leverage suggestion
MIN_RR_RATIO = 1.5             # Minimum Risk:Reward to consider tradeable
TP1_MULTIPLIER = 1.5           # TP1 = 1.5x risk distance
TP2_MULTIPLIER = 2.5           # TP2 = 2.5x risk distance
ATR_SL_MULTIPLIER = 1.5        # SL = 1.5x ATR from entry

# ── Signal Quality Gate ──────────────────────────
MIN_CONFLUENCE_SCORE = 3       # Minimum |score| to generate a trade setup
MIN_GRADE_TRADEABLE = "C+"     # Minimum grade to mark as tradeable
MIN_CONFIDENCE_PCT = 40        # Minimum confidence % to show trade
VOLUME_CONFIRMATION = True     # Require rising volume for trade setups

# ── ADX / Trend Settings ─────────────────────────
ADX_PERIOD = 14
ADX_STRONG_TREND = 25          # ADX > 25 = strong trend
ADX_WEAK_TREND = 15            # ADX 15-25 = weak trend
STOCH_K_PERIOD = 14
STOCH_D_PERIOD = 3
STOCH_OVERBOUGHT = 80
STOCH_OVERSOLD = 20
