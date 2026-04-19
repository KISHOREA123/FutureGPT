import ccxt
import pandas as pd
import time
import logging
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from config import (
    CANDLE_LIMIT, API_MAX_RETRIES, API_RETRY_DELAY, API_RETRY_BACKOFF,
    TIMEFRAMES, TRADING_PAIRS,
)

load_dotenv()
logger = logging.getLogger(__name__)

# ── Module-level cache for symbols ───────────────────────────
_all_symbols_cache = None
_cache_time = None


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


def fetch_ohlcv(
    symbol: str, timeframe: str = "1h", exchange_name: str = "binance", limit: int = None
) -> pd.DataFrame:
    """
    Fetch OHLCV candle data with exponential backoff retry logic.
    """
    exchange = get_exchange(exchange_name)
    symbol = normalize_symbol(symbol, exchange_name)
    limit = limit or CANDLE_LIMIT

    for attempt in range(1, API_MAX_RETRIES + 1):
        try:
            raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if not raw:
                return pd.DataFrame()

            df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df = df.astype(float)
            return df

        except ccxt.BadSymbol:
            raise ValueError(f"Symbol `{symbol}` not found on {exchange_name.capitalize()}.")

        except ccxt.RateLimitExceeded as e:
            wait_time = API_RETRY_DELAY * (API_RETRY_BACKOFF ** (attempt - 1))
            logger.warning(
                f"Rate limited on {symbol} {timeframe}, waiting {wait_time:.1f}s "
                f"(attempt {attempt}/{API_MAX_RETRIES})"
            )
            if attempt < API_MAX_RETRIES:
                time.sleep(wait_time)
            else:
                logger.error(f"Rate limit exceeded for {symbol} {timeframe} after {API_MAX_RETRIES} retries")
                return pd.DataFrame()

        except ccxt.NetworkError as e:
            wait_time = API_RETRY_DELAY * (API_RETRY_BACKOFF ** (attempt - 1))
            if attempt < API_MAX_RETRIES:
                logger.warning(
                    f"Network error on {symbol} {timeframe}: {e} — "
                    f"retrying in {wait_time:.1f}s ({attempt}/{API_MAX_RETRIES})"
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Network error fetching {symbol} {timeframe} after {API_MAX_RETRIES} retries: {e}")
                return pd.DataFrame()

        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching {symbol} {timeframe}: {e}")
            return pd.DataFrame()

        except Exception as e:
            if attempt < API_MAX_RETRIES:
                wait_time = API_RETRY_DELAY * (API_RETRY_BACKOFF ** (attempt - 1))
                logger.warning(
                    f"Error fetching {symbol} {timeframe}: {e} — "
                    f"retrying in {wait_time:.1f}s ({attempt}/{API_MAX_RETRIES})"
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Error fetching {symbol} {timeframe} after {API_MAX_RETRIES} retries: {e}")
                return pd.DataFrame()

    return pd.DataFrame()


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


def fetch_multi_timeframe(symbol: str, timeframes: list = None) -> dict:
    """
    Fetch data for multiple timeframes using concurrent execution.
    Returns dict of {timeframe: DataFrame}.
    """
    timeframes = timeframes or TIMEFRAMES
    data = {}
    max_workers = min(len(timeframes), 2)

    def _fetch_single(tf):
        df, exch = fetch_from_both(symbol, tf)
        return tf, df, exch

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_fetch_single, tf): tf for tf in timeframes}
            for future in as_completed(futures):
                try:
                    tf, df, exch = future.result(timeout=60)
                    if not df.empty:
                        data[tf] = {"df": df, "exchange": exch}
                except Exception as e:
                    tf = futures[future]
                    logger.warning(f"Failed to fetch {symbol} {tf}: {e}")
    except Exception as e:
        logger.error(f"Parallel fetch failed for {symbol}: {e}")
        for tf in timeframes:
            try:
                df, exch = fetch_from_both(symbol, tf)
                if not df.empty:
                    data[tf] = {"df": df, "exchange": exch}
            except Exception:
                pass
            time.sleep(0.5)

    return data


def load_all_symbols(quote_currency: str = "USDT") -> list:
    """
    Fetch all available trading pairs from exchange. Caches for 10 minutes.
    """
    global _all_symbols_cache, _cache_time

    if (
        _all_symbols_cache is not None
        and _cache_time is not None
        and (datetime.now() - _cache_time).total_seconds() < 600
    ):
        return _all_symbols_cache

    try:
        exchange = get_exchange("binance")
        exchange.load_markets()
        all_symbols = sorted([
            s for s in exchange.symbols
            if s.endswith(f"/{quote_currency}")
            and ":" not in s
            and ".P" not in s
        ])
        _all_symbols_cache = all_symbols
        _cache_time = datetime.now()
        logger.info(f"Loaded {len(all_symbols)} {quote_currency} pairs from exchange")
        return all_symbols
    except Exception as e:
        logger.error(f"Failed to load market symbols: {e}")
        return TRADING_PAIRS


def search_symbol(query: str) -> list:
    """Search for a symbol by partial name."""
    all_symbols = load_all_symbols()
    query = query.upper().strip()

    exact = f"{query}/USDT" if "/" not in query else query
    if exact in all_symbols:
        return [exact]

    matches = [s for s in all_symbols if s.split("/")[0].startswith(query)]
    if not matches:
        matches = [s for s in all_symbols if query in s.split("/")[0]]

    return matches[:20]


def fetch_close_prices_bulk(symbols: list, timeframe: str = "1h", limit: int = 50) -> dict:
    """Fetch close prices for multiple symbols (for correlation filter)."""
    price_data = {}
    for symbol in symbols:
        try:
            df = fetch_ohlcv(symbol, timeframe, limit=limit)
            if not df.empty:
                price_data[symbol] = df
        except Exception:
            pass
        time.sleep(0.3)
    return price_data
