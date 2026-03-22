"""
services/indicator_service.py — Technical indicator computation.

Fetches OHLCV kline data from Binance and computes:
  • RSI  (Relative Strength Index, 14-period)
  • MACD (Moving Average Convergence Divergence, 12/26/9)
  • EMA  (Exponential Moving Average, 20 & 50 period)

All indicators are implemented with pure pandas — no third-party TA library needed.
pandas-ta was removed because it is abandoned and has no working PyPI release for
Python 3.10+. The math here is equivalent and fully tested.

No API key required — Binance klines endpoint is public.
"""

import logging
from dataclasses import dataclass

import aiohttp
import pandas as pd

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

BINANCE_KLINES  = "https://api.binance.com/api/v3/klines"
KLINE_INTERVAL  = "1h"    # 1-hour candles — balanced signal quality
KLINE_LIMIT     = 100     # 100 candles is enough for all indicator warmup
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)

RSI_OVERSOLD   = 35
RSI_OVERBOUGHT = 65


# ── Data container ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Indicators:
    """Computed TA indicators for one symbol."""
    symbol:    str
    price:     float
    rsi:       float   # RSI(14)
    macd:      float   # MACD line
    macd_sig:  float   # Signal line
    macd_hist: float   # Histogram = macd - signal
    ema_20:    float
    ema_50:    float

    @property
    def ema_trend(self) -> str:
        if self.price > self.ema_20 > self.ema_50:
            return "BULLISH"
        if self.price < self.ema_20 < self.ema_50:
            return "BEARISH"
        return "NEUTRAL"

    @property
    def macd_cross(self) -> str:
        if self.macd > self.macd_sig and self.macd_hist > 0:
            return "BULLISH"
        if self.macd < self.macd_sig and self.macd_hist < 0:
            return "BEARISH"
        return "NEUTRAL"

    @property
    def rsi_zone(self) -> str:
        if self.rsi <= RSI_OVERSOLD:
            return "OVERSOLD"
        if self.rsi >= RSI_OVERBOUGHT:
            return "OVERBOUGHT"
        return "NEUTRAL"


# ── Public API ────────────────────────────────────────────────────────────────

async def compute_indicators(symbol: str, interval: str = "1h") -> Indicators:
    """
    Fetch Binance OHLCV klines for `symbol`/USDT and compute all indicators.

    Raises:
        ValueError: Unknown symbol or empty response.
        aiohttp.ClientError: Network failure.
    """
    symbol = symbol.upper()
    pair   = f"{symbol}USDT"

    logger.info("Fetching klines: %s  interval=%s  limit=%d", pair, interval, KLINE_LIMIT)
    raw = await _fetch_klines(pair, interval)

    df   = _build_dataframe(raw)
    df   = _apply_indicators(df)
    last = df.iloc[-1]

    return Indicators(
        symbol    = symbol,
        price     = float(last["close"]),
        rsi       = round(float(last["rsi"]),       2),
        macd      = round(float(last["macd"]),       4),
        macd_sig  = round(float(last["macd_sig"]),   4),
        macd_hist = round(float(last["macd_hist"]),  4),
        ema_20    = round(float(last["ema_20"]),      4),
        ema_50    = round(float(last["ema_50"]),      4),
    )


# ── Indicator formatting (used by signal_service) ─────────────────────────────

def format_indicators_block(ind: Indicators) -> str:
    """Return a compact Telegram HTML card showing all indicators."""
    rsi_dot  = "🔴" if ind.rsi_zone   == "OVERBOUGHT" else ("🟢" if ind.rsi_zone   == "OVERSOLD" else "🟡")
    macd_dot = "🟢" if ind.macd_cross == "BULLISH"    else ("🔴" if ind.macd_cross == "BEARISH"  else "🟡")
    ema_dot  = "🟢" if ind.ema_trend  == "BULLISH"    else ("🔴" if ind.ema_trend  == "BEARISH"  else "🟡")

    return (
        f"<b>📐 Technical Indicators  ({ind.symbol}/USDT · 1H)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Price</b>       <code>${ind.price:>14,.4f}</code>\n"
        f"{rsi_dot} <b>RSI (14)</b>    <code>{ind.rsi:>14.2f}</code>  <i>{ind.rsi_zone}</i>\n"
        f"{macd_dot} <b>MACD</b>        <code>{ind.macd:>+14.4f}</code>  <i>{ind.macd_cross} cross</i>\n"
        f"   <b>Signal</b>      <code>{ind.macd_sig:>+14.4f}</code>\n"
        f"   <b>Histogram</b>  <code>{ind.macd_hist:>+14.4f}</code>\n"
        f"{ema_dot} <b>EMA 20</b>      <code>${ind.ema_20:>14,.4f}</code>\n"
        f"   <b>EMA 50</b>      <code>${ind.ema_50:>14,.4f}</code>  <i>{ind.ema_trend}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _fetch_klines(pair: str, interval: str = KLINE_INTERVAL) -> list[list]:
    """Fetch raw kline data from Binance public endpoint."""
    params = {"symbol": pair, "interval": interval, "limit": KLINE_LIMIT}
    async with aiohttp.ClientSession() as session:
        async with session.get(BINANCE_KLINES, params=params, timeout=REQUEST_TIMEOUT) as resp:
            if resp.status == 400:
                raise ValueError(f"Unknown Binance symbol: {pair}")
            resp.raise_for_status()
            data = await resp.json()
    if not data:
        raise ValueError(f"Binance returned no kline data for {pair}")
    return data


def _build_dataframe(raw: list[list]) -> pd.DataFrame:
    """Convert Binance kline rows to a typed pandas DataFrame."""
    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore",
    ]
    df = pd.DataFrame(raw, columns=cols)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df.set_index("open_time", inplace=True)
    return df


def _apply_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute RSI, MACD, and EMA using pure pandas math.

    RSI(14):
        Uses Wilder's smoothing (exponential moving average of gains/losses).
        Equivalent to pandas_ta.rsi(length=14).

    MACD(12, 26, 9):
        macd      = EMA(close, 12) - EMA(close, 26)
        macd_sig  = EMA(macd, 9)
        macd_hist = macd - macd_sig

    EMA(20) and EMA(50):
        Standard exponential moving average via pandas ewm(span=N, adjust=False).
    """
    close = df["close"]

    # ── RSI ──────────────────────────────────────────────────────────────────
    delta  = close.diff()
    gain   = delta.clip(lower=0)
    loss   = (-delta).clip(lower=0)
    # Wilder's smoothing: alpha = 1/length, equivalent to EWM with com=length-1
    avg_gain = gain.ewm(com=13, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(com=13, min_periods=14, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, float("nan"))
    df["rsi"] = 100 - (100 / (1 + rs))

    # ── MACD ─────────────────────────────────────────────────────────────────
    ema12         = close.ewm(span=12, adjust=False).mean()
    ema26         = close.ewm(span=26, adjust=False).mean()
    df["macd"]    = ema12 - ema26
    df["macd_sig"]  = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]

    # ── EMA ──────────────────────────────────────────────────────────────────
    df["ema_20"] = close.ewm(span=20, adjust=False).mean()
    df["ema_50"] = close.ewm(span=50, adjust=False).mean()

    df.dropna(inplace=True)

    if df.empty:
        raise ValueError("Indicator computation produced empty DataFrame — not enough candles.")

    return df


# ── Public re-exports for pattern detection ───────────────────────────────────
# analyze_handler imports these to reuse already-fetched OHLCV data
async def fetch_ohlcv(symbol: str, interval: str = "1h") -> "pd.DataFrame":
    """
    Public helper: fetch + build DataFrame for a symbol.
    Used by analyze_handler to share OHLCV data between indicators and patterns.
    """
    pair = f"{symbol.upper()}USDT"
    raw  = await _fetch_klines(pair, interval)
    return _build_dataframe(raw)


def apply_indicators_to_df(df: "pd.DataFrame") -> "pd.DataFrame":
    """Public wrapper around _apply_indicators for external callers."""
    return _apply_indicators(df)