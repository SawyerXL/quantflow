"""
QuantFlow data service.

Handles CSV upload parsing, Yahoo Finance data fetching (with Redis cache),
OHLCV data validation, and preprocessing.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from io import BytesIO
from typing import Optional

import pandas as pd
import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Cache TTL: 24 hours in seconds
CACHE_TTL = 60 * 60 * 24
# External API timeout in seconds
API_TIMEOUT = 10.0

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

# Column name aliases: every recognized variant maps to the canonical lowercase name
_COLUMN_ALIASES: dict[str, str] = {
    # close
    "close": "close",
    "closing_price": "close",
    "closing price": "close",
    "adj close": "close",
    "adjusted close": "close",
    "last": "close",
    "price": "close",
    # open
    "open": "open",
    "opening_price": "open",
    "opening price": "open",
    # high
    "high": "high",
    # low
    "low": "low",
    # volume
    "volume": "volume",
    "vol": "volume",
    # date
    "date": "date",
    "datetime": "date",
    "time": "date",
    "timestamp": "date",
    "dt": "date",
}

# Date formats to try when parsing, in order of preference
_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y%m%d",
    "%b %d %Y",
    "%B %d %Y",
    "%d %b %Y",
    "%d %B %Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%f",
]


@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Redis cache helper
# ---------------------------------------------------------------------------


class RedisCache:
    """Async Redis cache client with JSON serialization."""

    def __init__(self):
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                import redis.asyncio as aioredis

                self._client = aioredis.from_url(
                    settings.REDIS_URL,
                    socket_connect_timeout=3,
                    socket_timeout=3,
                    decode_responses=False,
                )
            except Exception as exc:
                logger.warning("Redis unavailable, caching disabled: %s", exc)
                return None
        return self._client

    def _cache_key(self, prefix: str, *args: str) -> str:
        raw = f"{prefix}:{':'.join(args)}"
        return f"quantflow:data:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

    async def get(self, prefix: str, *args: str) -> pd.DataFrame | None:
        client = await self._get_client()
        if client is None:
            return None

        key = self._cache_key(prefix, *args)
        try:
            raw = await client.get(key)
            if raw:
                df = pd.read_parquet(BytesIO(raw))
                logger.debug("Cache HIT: %s", key)
                return df
        except Exception as exc:
            logger.warning("Redis read error: %s", exc)
        return None

    async def set(self, prefix: str, df: pd.DataFrame, *args: str) -> None:
        client = await self._get_client()
        if client is None:
            return

        key = self._cache_key(prefix, *args)
        try:
            buf = BytesIO()
            df.to_parquet(buf, index=True, compression="zstd")
            await client.setex(key, CACHE_TTL, buf.getvalue())
            logger.debug("Cache SET: %s (ttl=%ds)", key, CACHE_TTL)
        except Exception as exc:
            logger.warning("Redis write error: %s", exc)


# Global cache singleton
_data_cache = RedisCache()


# ---------------------------------------------------------------------------
# 1. CSV file parsing
# ---------------------------------------------------------------------------


def _detect_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect and rename columns based on aliases.
    Columns not recognized are dropped.
    """
    rename_map: dict[str, str] = {}
    seen_canonical: set[str] = set()

    for col in df.columns:
        col_lower = str(col).strip().lower()
        canonical = _COLUMN_ALIASES.get(col_lower)
        if canonical is None:
            # Try partial matching
            for pattern, target in _COLUMN_ALIASES.items():
                if pattern in col_lower or col_lower in pattern:
                    canonical = target
                    break

        if canonical is not None:
            if canonical not in seen_canonical:
                rename_map[col] = canonical
                seen_canonical.add(canonical)

    if rename_map:
        df = df.rename(columns=rename_map)

    # Keep only recognized and useful columns
    keep_cols = [c for c in df.columns if c in _COLUMN_ALIASES.values()]
    return df[keep_cols]


def _parse_dates(dates: pd.Series) -> pd.DatetimeIndex:
    """
    Try to parse dates from various formats.
    Falls back to numeric timestamp interpretation.
    """
    # If already datetime, return directly
    if pd.api.types.is_datetime64_any_dtype(dates):
        return pd.DatetimeIndex(dates)

    # Try as numeric timestamp (seconds or ms since epoch)
    if pd.api.types.is_numeric_dtype(dates):
        vals = dates.dropna()
        if len(vals) > 0:
            # If values look like millisecond timestamps ( > 1e10 ), treat as ms
            if vals.iloc[0] > 1e10:
                return pd.to_datetime(dates, unit="ms", errors="coerce")
            else:
                return pd.to_datetime(dates, unit="s", errors="coerce")

    # Try string formats
    return pd.to_datetime(dates, errors="coerce")


def parse_csv_upload(file: BytesIO | bytes | str) -> pd.DataFrame:
    """
    Parse an uploaded CSV file into a standardized OHLCV DataFrame.

    Args:
        file: File-like object, bytes, or path string containing CSV data.

    Returns:
        Standardized DataFrame with lowercase column names and DatetimeIndex.

    Raises:
        ValueError: With a user-friendly message describing what went wrong.
    """
    logger.info("Parsing CSV upload")

    # Read CSV
    try:
        if isinstance(file, bytes):
            df = pd.read_csv(BytesIO(file))
        elif isinstance(file, str):
            df = pd.read_csv(file)
        else:
            df = pd.read_csv(file)
    except Exception as exc:
        raise ValueError(f"Failed to read CSV file: {exc}") from exc

    if df.empty:
        raise ValueError("CSV file is empty — no data rows found.")

    logger.debug("CSV loaded: %d rows, %d columns: %s", len(df), len(df.columns), list(df.columns))

    # Detect and rename columns
    df = _detect_columns(df)

    if "close" not in df.columns:
        raise ValueError(
            "Missing required close price column. "
            "Expected one of: close, Close, CLOSE, closing_price, price, last. "
            f"Found columns: {list(df.columns)}"
        )

    # Parse dates
    if "date" in df.columns:
        df["date"] = _parse_dates(df["date"])
        na_dates = df["date"].isna().sum()
        if na_dates > 0:
            raise ValueError(
                f"Could not parse {na_dates} date value(s). "
                f"Supported formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, timestamps. "
                f"First bad value at row {df['date'].isna().idxmax()}."
            )
        df = df.set_index("date")
    else:
        raise ValueError(
            "No date column found. Expected one of: date, datetime, time, timestamp, dt."
        )

    # Ensure numeric columns
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Check for NaN in close
    na_close = df["close"].isna().sum()
    if na_close > 0:
        raise ValueError(
            f"Close price column has {na_close} missing value(s) or non-numeric entries."
        )

    # Check for negative / zero close prices
    neg_close = (df["close"] <= 0).sum()
    if neg_close > 0:
        raise ValueError(
            f"Close price column has {neg_close} value(s) that are zero or negative. "
            f"Prices must be positive."
        )

    # Sort by date and deduplicate index
    df = df.sort_index()
    dupes = df.index.duplicated().sum()
    if dupes > 0:
        logger.warning("Removing %d duplicate date rows (keeping last)", dupes)
        df = df[~df.index.duplicated(keep="last")]

    # Drop rows where close is NaN
    df = df.dropna(subset=["close"])

    # Keep only recognized columns
    keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep]

    logger.info("CSV parsed successfully: %d rows, columns=%s", len(df), keep)
    return df


# ---------------------------------------------------------------------------
# 2. Yahoo Finance data fetching
# ---------------------------------------------------------------------------


async def get_yahoo_data(
    ticker: str,
    start_date: str,
    end_date: str,
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Fetch OHLCV data from Yahoo Finance with Redis caching.

    Args:
        ticker: Symbol to fetch (e.g., AAPL, SPY, BTC-USD).
        start_date: Start date as "YYYY-MM-DD".
        end_date: End date as "YYYY-MM-DD".
        interval: Bar interval ("1d", "1wk", "1h", etc.).

    Returns:
        Standardized DataFrame with lowercase columns and DatetimeIndex.

    Raises:
        ValueError: If the ticker is not found, data is empty, or request fails.
    """
    ticker = ticker.strip().upper()
    if not re.match(r"^[A-Z0-9.\-^=]{1,20}$", ticker):
        raise ValueError(f"Invalid ticker symbol: {ticker}")

    # Check cache first (local Redis, then Upstash)
    cached = await _data_cache.get("yahoo", ticker, start_date, end_date, interval)
    if cached is not None and not cached.empty:
        logger.info("Cache HIT (Redis) for %s", ticker)
        return cached

    # Try Upstash cache as fallback
    cache_key = f"ticker:{ticker}:{start_date}:{end_date}"
    try:
        from app.core.cache import redis_cache as _upstash
        raw = await _upstash.get(cache_key)
    except ImportError:
        raw = None
    if raw:
        try:
            import json
            data = json.loads(raw)
            df = pd.DataFrame(data["data"], index=pd.DatetimeIndex(data["index"]))
            logger.info("Cache HIT (Upstash) for %s", ticker)
            return df
        except Exception:
            pass

    logger.info("Fetching Yahoo data for %s [%s → %s, %s]", ticker, start_date, end_date, interval)

    try:
        import yfinance as yf
    except ImportError:
        raise RuntimeError("yfinance package is not installed")

    try:
        # Fetch 60 extra days for indicator warmup (e.g., SMA 50 needs 50 prior bars)
        from datetime import timedelta
        extended_start = (pd.Timestamp(start_date) - timedelta(days=90)).strftime("%Y-%m-%d")

        ticker_obj = yf.Ticker(ticker)

        # Run yfinance in a thread with timeout
        df = await asyncio.wait_for(
            asyncio.to_thread(
                ticker_obj.history,
                start=extended_start,
                end=end_date,
                interval=interval,
                auto_adjust=True,   # Use adjusted close prices
                actions=False,      # Don't need dividend/split data
            ),
            timeout=API_TIMEOUT,
        )
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"Yahoo Finance request timed out after {API_TIMEOUT}s for {ticker}"
        )
    except Exception as exc:
        # Distinguish common errors
        msg = str(exc).lower()
        if "not found" in msg or "no data" in msg or "404" in msg:
            raise ValueError(
                f"Ticker '{ticker}' not found on Yahoo Finance. "
                f"Check the symbol and try again."
            )
        if "rate limit" in msg or "too many requests" in msg:
            raise RuntimeError(
                "Yahoo Finance rate limit reached. Please wait and try again."
            )
        raise RuntimeError(f"Yahoo Finance error for {ticker}: {exc}") from exc

    if df is None or df.empty:
        raise ValueError(
            f"No data returned for ticker '{ticker}' in range {start_date} to {end_date}. "
            f"The ticker may be delisted, have no data for this period, or the market "
            f"may be closed on these dates."
        )

    logger.debug("Yahoo returned %d rows for %s", len(df), ticker)

    # Standardize
    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

    # Ensure we have the expected columns
    for col in ["open", "high", "low", "close", "volume"]:
        if col not in df.columns:
            df[col] = np.nan

    # Drop rows where close is NaN (non-trading days already excluded by yfinance)
    df = df.dropna(subset=["close"])

    # Clean up: dividends and stock splits columns from yfinance
    keep_cols = ["open", "high", "low", "close", "volume"]
    df = df[[c for c in keep_cols if c in df.columns]]

    if len(df) < 10:
        raise ValueError(
            f"Only {len(df)} trading days returned for '{ticker}'. "
            f"This may be a very low-liquidity asset or the date range is too narrow."
        )

    # Cache the result (Redis + Upstash)
    await _data_cache.set("yahoo", df, ticker, start_date, end_date, interval)

    # Also cache in Upstash (JSON, since Upstash REST doesn't support binary)
    try:
        import json
        cache_data = json.dumps({
            "index": [str(d) for d in df.index],
            "data": {col: df[col].tolist() for col in df.columns},
        })
        from app.core.cache import redis_cache as _upstash_write
        await _upstash_write.set(cache_key, cache_data, ttl=86400)
    except ImportError:
        pass
    except Exception:
        logger.debug("Upstash cache write failed (non-critical)")

    return df


# ---------------------------------------------------------------------------
# 3. Data validation
# ---------------------------------------------------------------------------


def validate_ohlcv(df: pd.DataFrame) -> ValidationResult:
    """
    Validate an OHLCV DataFrame and return errors/warnings.

    Checks performed:
    - Minimum 60 rows
    - close price > 0 for all rows
    - high >= low (if both columns present)
    - high >= open, close, low (if OHLC columns present)
    - low <= open, close, high
    - No duplicate dates in index
    - Warn on large date gaps (> 10 business days)
    - Warn on zero or negative volume rows

    Returns:
        ValidationResult with is_valid, errors[], and warnings[].
    """
    result = ValidationResult()

    if df is None:
        result.errors.append("DataFrame is None")
        result.is_valid = False
        return result

    if not isinstance(df, pd.DataFrame):
        result.errors.append(f"Expected DataFrame, got {type(df).__name__}")
        result.is_valid = False
        return result

    # Row count
    if len(df) < 60:
        result.errors.append(
            f"Insufficient data: {len(df)} rows (minimum 60 trading days required)"
        )
        result.is_valid = False

    # close column
    if "close" not in df.columns:
        result.errors.append("Missing required column: close")
        result.is_valid = False
        return result

    # close must be positive
    neg_close = (df["close"] <= 0).sum()
    if neg_close > 0:
        result.errors.append(
            f"Close price has {neg_close} non-positive value(s). All close prices must be > 0."
        )
        result.is_valid = False

    # Check for infinity
    inf_mask = df["close"].apply(lambda x: np.isinf(x) if isinstance(x, float) else False)
    if inf_mask.any():
        result.errors.append(
            f"Close price has {inf_mask.sum()} infinite value(s)."
        )
        result.is_valid = False

    # NaN in close
    na_close = df["close"].isna().sum()
    if na_close > 0:
        result.errors.append(
            f"Close price has {na_close} NaN value(s) — preprocess data to fill or drop them."
        )
        result.is_valid = False

    # high >= low check
    if "high" in df.columns and "low" in df.columns:
        high = pd.to_numeric(df["high"], errors="coerce")
        low = pd.to_numeric(df["low"], errors="coerce")

        violation = (high < low).sum()
        if violation > 0:
            result.errors.append(
                f"high < low in {violation} row(s) — high must be >= low"
            )
            result.is_valid = False

        # High must be >= open, close, low
        if "open" in df.columns:
            open_p = pd.to_numeric(df["open"], errors="coerce")
            high_bad = (high < open_p) | (high < pd.to_numeric(df["close"], errors="coerce"))
            if high_bad.sum() > 0:
                result.errors.append(
                    f"high < open or close in {high_bad.sum()} row(s)"
                )
                result.is_valid = False

        # Low must be <= open, close, high
        if "open" in df.columns:
            low_bad = (low > open_p) | (low > pd.to_numeric(df["close"], errors="coerce"))
            if low_bad.sum() > 0:
                result.errors.append(
                    f"low > open or close in {low_bad.sum()} row(s)"
                )
                result.is_valid = False

    # Duplicate dates
    if isinstance(df.index, pd.DatetimeIndex):
        dupes = df.index.duplicated().sum()
        if dupes > 0:
            result.errors.append(
                f"Found {dupes} duplicate date(s) in index"
            )
            result.is_valid = False

    # --- Warnings (non-fatal) ---

    # Large gaps between dates
    if isinstance(df.index, pd.DatetimeIndex) and len(df.index) > 1:
        gaps = df.index.to_series().diff().dropna()
        # Gaps larger than 10 calendar days
        big_gaps = gaps[gaps > pd.Timedelta(days=10)]
        if len(big_gaps) > 0:
            result.warnings.append(
                f"{len(big_gaps)} large date gap(s) found (>{10} days). "
                f"Largest: {big_gaps.max().days} days."
            )

    # Volume warnings
    if "volume" in df.columns:
        volumes = pd.to_numeric(df["volume"], errors="coerce")
        zero_vol = (volumes <= 0).sum()
        if zero_vol > 0:
            pct = zero_vol / len(volumes) * 100
            result.warnings.append(
                f"{zero_vol} row(s) ({pct:.1f}%) have zero or negative volume"
            )

    # Warn if close has suspiciously large outliers
    if len(df) > 0:
        close_mean = df["close"].mean()
        close_std = df["close"].std()
        if close_std > 0:
            outlier_threshold = 5.0  # standard deviations
            outliers = (abs(df["close"] - close_mean) > outlier_threshold * close_std).sum()
            if outliers > 0:
                result.warnings.append(
                    f"{outliers} potential price outlier(s) detected "
                    f"(>{outlier_threshold}σ from mean)"
                )

    return result


# ---------------------------------------------------------------------------
# 4. Data preprocessing
# ---------------------------------------------------------------------------


def preprocess_data(
    df: pd.DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Preprocess OHLCV data for backtesting.

    Steps:
    1. Filter by date range.
    2. Forward-fill missing values (nas, holidays).
    3. Drop rows where close is still missing after ffill.

    Args:
        df: Standardized OHLCV DataFrame with DatetimeIndex.
        start_date: Optional start date filter ("YYYY-MM-DD").
        end_date: Optional end date filter ("YYYY-MM-DD").

    Returns:
        Cleaned DataFrame ready for backtesting.
    """
    if df is None or df.empty:
        raise ValueError("Cannot preprocess empty DataFrame")

    df = df.copy()

    # Normalize timezone (yfinance returns tz-aware timestamps for US stocks)
    if hasattr(df.index, "tz") and df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)

    # Filter by date
    if start_date:
        start_ts = pd.Timestamp(start_date)
        df = df[df.index >= start_ts]
        logger.debug("Filtered start_date=%s → %d rows", start_date, len(df))

    if end_date:
        end_ts = pd.Timestamp(end_date)
        df = df[df.index <= end_ts]
        logger.debug("Filtered end_date=%s → %d rows", end_date, len(df))

    if df.empty:
        raise ValueError(
            f"No data remaining after date filter ({start_date} to {end_date})"
        )

    # Ensure only known columns remain
    keep = [c for c in ["open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep]

    # Convert all to numeric
    for col in keep:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Forward-fill: carry last known value over gaps
    n_before = df.isna().sum().sum()
    df = df.ffill()
    n_after = df.isna().sum().sum()
    if n_before > n_after:
        logger.debug("Forward-filled %d missing value(s)", n_before - n_after)

    # Drop rows where close is still missing (start of series before any data)
    df = df.dropna(subset=["close"])

    # Drop rows where all values are NaN
    df = df.dropna(how="all")

    logger.info("Preprocessed: %d rows, columns=%s", len(df), list(df.columns))
    return df


# ---------------------------------------------------------------------------
# Symbol search
# ---------------------------------------------------------------------------


async def search_symbols(query: str) -> list[dict]:
    """Search for symbols matching the query string."""
    common_symbols = [
        {"symbol": "AAPL", "name": "Apple Inc."},
        {"symbol": "MSFT", "name": "Microsoft Corp."},
        {"symbol": "GOOGL", "name": "Alphabet Inc."},
        {"symbol": "AMZN", "name": "Amazon.com Inc."},
        {"symbol": "META", "name": "Meta Platforms Inc."},
        {"symbol": "TSLA", "name": "Tesla Inc."},
        {"symbol": "NVDA", "name": "NVIDIA Corp."},
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF"},
        {"symbol": "QQQ", "name": "Invesco QQQ Trust"},
        {"symbol": "IWM", "name": "iShares Russell 2000 ETF"},
        {"symbol": "DIA", "name": "SPDR Dow Jones ETF"},
        {"symbol": "BTC-USD", "name": "Bitcoin USD"},
        {"symbol": "ETH-USD", "name": "Ethereum USD"},
        {"symbol": "SOL-USD", "name": "Solana USD"},
        {"symbol": "EURUSD=X", "name": "EUR/USD"},
        {"symbol": "GC=F", "name": "Gold Futures"},
        {"symbol": "CL=F", "name": "Crude Oil Futures"},
    ]
    q = query.upper().strip()
    return [
        s for s in common_symbols
        if q in s["symbol"] or q in s["name"].upper()
    ]
