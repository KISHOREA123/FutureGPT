import ccxt
import pandas as pd
import asyncio
from config import CANDLE_LIMIT
import os
from dotenv import load_dotenv

load_dotenv()

def get_exchange(name: str = "binance"):
    """Initialize exchange instance."""
    name = name.lower()
    if name == "binance":
        exchange = ccxt.binance({
            "apiKey": os.getenv("BINANCE_API_KEY", ""),
            "secret": os.getenv("BINANCE_SECRET", ""),
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })
    elif name == "bybit":
        exchange = ccxt.bybit({
            "apiKey": os.getenv("BYBIT_API_KEY", ""),
            "secret": os.getenv("BYBIT_SECRET", ""),
            "enableRateLimit": True,
        })
    else:
        raise ValueError(f"Unsupported exchange: {name}")
    return exchange


def normalize_symbol(symbol: str, exchange_name: str) -> str:
    """Normalize symbol to exchange format. e.g. BTC -> BTC/USDT"""
    symbol = symbol.upper().strip()
    if "/" not in symbol:
        symbol = f"{symbol}/USDT"
    return symbol


def fetch_ohlcv(symbol: str, timeframe: str = "1h", exchange_name: str = "binance") -> pd.DataFrame:
    """Fetch OHLCV candle data from exchange."""
    exchange = get_exchange(exchange_name)
    symbol = normalize_symbol(symbol, exchange_name)

    try:
        raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=CANDLE_LIMIT)
    except ccxt.BadSymbol:
        raise ValueError(f"Symbol `{symbol}` not found on {exchange_name.capitalize()}.")
    except ccxt.NetworkError as e:
        raise ConnectionError(f"Network error fetching data from {exchange_name}: {e}")
    except Exception as e:
        raise RuntimeError(f"Error fetching OHLCV: {e}")

    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df.astype(float)
    return df


def fetch_from_both(symbol: str, timeframe: str) -> tuple[pd.DataFrame, str]:
    """Try Binance first, fallback to Bybit."""
    for exchange_name in ["binance", "bybit"]:
        try:
            df = fetch_ohlcv(symbol, timeframe, exchange_name)
            if df is not None and len(df) >= 50:
                return df, exchange_name
        except Exception:
            continue
    raise RuntimeError(f"Could not fetch data for {symbol} from Binance or Bybit.")
