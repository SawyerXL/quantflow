"""
Unit tests for QuantFlow data service.

Tests cover CSV parsing, data validation, preprocessing, and
Yahoo Finance data fetching (with mocked yfinance and Redis).
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.data_service import (
    ValidationResult,
    parse_csv_upload,
    validate_ohlcv,
    preprocess_data,
    get_yahoo_data,
    _detect_columns,
    _parse_dates,
    _DATE_FORMATS,
)

# ============================================================================
# Helpers
# ============================================================================


def make_ohlcv_df(
    days: int = 252,
    start_price: float = 100.0,
    seed: int = 42,
    close_only: bool = False,
) -> pd.DataFrame:
    """Generate a valid OHLCV DataFrame for testing.

    Guarantees correct OHLC relationships: high >= max(open, close),
    low <= min(open, close).
    """
    dates = pd.date_range(end=pd.Timestamp.now(), periods=days, freq="B")
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0005, 0.015, days)
    close = start_price * np.cumprod(1 + returns)

    if close_only:
        return pd.DataFrame({"close": close}, index=dates)

    # Build open first (yesterday's close ± small gap)
    open_p = close * rng.uniform(0.995, 1.005, days)

    # high = max(open, close) + positive noise
    session_max = np.maximum(open_p, close)
    high = session_max + np.abs(rng.normal(0, close * 0.005, days))

    # low = min(open, close) - positive noise
    session_min = np.minimum(open_p, close)
    low = session_min - np.abs(rng.normal(0, close * 0.005, days))

    return pd.DataFrame(
        {
            "open": open_p,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.integers(100_000, 10_000_000, days),
        },
        index=dates,
    )


def make_csv_bytes(df: pd.DataFrame, include_date: bool = True) -> BytesIO:
    """Convert a DataFrame to CSV bytes for upload testing."""
    out = df.copy()
    if include_date and isinstance(out.index, pd.DatetimeIndex):
        out = out.reset_index()
        out.rename(columns={"index": "date"}, inplace=True)
    buf = BytesIO()
    out.to_csv(buf, index=False)
    buf.seek(0)
    return buf


# ============================================================================
# CSV parsing tests
# ============================================================================


class TestCSVParsing:
    """Test parse_csv_upload with various formats."""

    # -- happy path --

    def test_standard_ohlcv_csv(self):
        df = make_ohlcv_df(100)
        buf = make_csv_bytes(df)
        result = parse_csv_upload(buf)

        assert isinstance(result.index, pd.DatetimeIndex)
        assert "close" in result.columns
        assert len(result) == 100

    def test_close_only_csv(self):
        """CSV with only date and close columns."""
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        df = pd.DataFrame({"date": dates, "close": np.linspace(100, 200, 100)})
        buf = make_csv_bytes(df)
        result = parse_csv_upload(buf)

        assert "close" in result.columns
        assert len(result) == 100
        assert isinstance(result.index, pd.DatetimeIndex)

    # -- column aliases --

    def test_uppercase_columns(self):
        """Columns in UPPERCASE should be recognized."""
        dates = pd.date_range("2024-01-01", periods=80, freq="B")
        df = pd.DataFrame({
            "Date": dates,
            "Close": np.linspace(100, 150, 80),
            "Open": np.linspace(99, 149, 80),
            "High": np.linspace(101, 152, 80),
            "Low": np.linspace(98, 148, 80),
            "Volume": np.full(80, 1000000),
        })
        buf = make_csv_bytes(df)
        result = parse_csv_upload(buf)

        assert set(result.columns) == {"open", "high", "low", "close", "volume"}
        assert len(result) == 80

    def test_closing_price_alias(self):
        """'closing_price' should be recognized as close."""
        dates = pd.date_range("2024-01-01", periods=80, freq="B")
        df = pd.DataFrame({
            "date": dates,
            "closing_price": np.linspace(100, 150, 80),
        })
        buf = make_csv_bytes(df)
        result = parse_csv_upload(buf)
        assert "close" in result.columns

    def test_adj_close_alias(self):
        """'Adjusted Close' should be recognized."""
        dates = pd.date_range("2024-01-01", periods=80, freq="B")
        df = pd.DataFrame({
            "date": dates,
            "adjusted close": np.linspace(100, 150, 80),
            "volume": np.full(80, 500000),
        })
        buf = make_csv_bytes(df)
        result = parse_csv_upload(buf)
        assert "close" in result.columns

    # -- date format parsing --

    def test_date_format_YYYY_MM_DD(self):
        dates = pd.date_range("2024-01-01", periods=80, freq="B")
        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "close": np.linspace(100, 150, 80),
        })
        buf = make_csv_bytes(df)
        result = parse_csv_upload(buf)
        assert len(result) == 80

    def test_date_format_MM_DD_YYYY(self):
        df = pd.DataFrame({
            "date": ["01/15/2024", "01/16/2024", "01/17/2024", "01/18/2024",
                     "01/19/2024", "01/22/2024", "01/23/2024", "01/24/2024",
                     "01/25/2024", "01/26/2024", "01/29/2024", "01/30/2024",
                     "01/31/2024", "02/01/2024", "02/02/2024", "02/05/2024",
                     "02/06/2024", "02/07/2024", "02/08/2024", "02/09/2024",
                     "02/12/2024", "02/13/2024", "02/14/2024", "02/15/2024",
                     "02/16/2024", "02/20/2024", "02/21/2024", "02/22/2024",
                     "02/23/2024", "02/26/2024", "02/27/2024", "02/28/2024",
                     "02/29/2024", "03/01/2024", "03/04/2024", "03/05/2024",
                     "03/06/2024", "03/07/2024", "03/08/2024", "03/11/2024",
                     "03/12/2024", "03/13/2024", "03/14/2024", "03/15/2024",
                     "03/18/2024", "03/19/2024", "03/20/2024", "03/21/2024",
                     "03/22/2024", "03/25/2024", "03/26/2024", "03/27/2024",
                     "03/28/2024", "03/29/2024", "04/01/2024", "04/02/2024",
                     "04/03/2024", "04/04/2024", "04/05/2024", "04/08/2024",
                     "04/09/2024", "04/10/2024", "04/11/2024", "04/12/2024"],
            "close": np.linspace(100, 200, 64),
        })
        buf = make_csv_bytes(df)
        result = parse_csv_upload(buf)
        assert len(result) == 64
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_date_column_datetime_name(self):
        """Column named 'datetime' should be recognized."""
        dates = pd.date_range("2024-01-01", periods=65, freq="B")
        df = pd.DataFrame({
            "datetime": dates,
            "close": np.linspace(100, 150, 65),
        })
        buf = make_csv_bytes(df)
        result = parse_csv_upload(buf)
        assert len(result) == 65

    def test_date_timestamp_column(self):
        """Timestamp column should parse as dates."""
        dates = pd.date_range("2024-01-01", periods=65, freq="B")
        df = pd.DataFrame({
            "timestamp": dates.astype(np.int64) // 10**9,  # Unix timestamps
            "close": np.linspace(100, 150, 65),
        })
        buf = make_csv_bytes(df)
        result = parse_csv_upload(buf)
        assert len(result) == 65
        assert isinstance(result.index, pd.DatetimeIndex)

    # -- error cases --

    def test_missing_close_column_raises(self):
        """Should raise with clear message when close column is absent."""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=50, freq="B"),
            "volume": np.ones(50),
        })
        buf = make_csv_bytes(df)
        with pytest.raises(ValueError, match="Missing required close price column"):
            parse_csv_upload(buf)

    def test_empty_csv_raises(self):
        buf = BytesIO(b"")
        with pytest.raises(ValueError, match="Failed to read CSV"):
            parse_csv_upload(buf)

    def test_empty_dataframe_raises(self):
        buf = BytesIO(b"date,close\n")
        with pytest.raises(ValueError, match="empty"):
            parse_csv_upload(buf)

    def test_no_date_column_raises(self):
        df = pd.DataFrame({"close": [100, 101, 102]})
        buf = make_csv_bytes(df, include_date=False)
        with pytest.raises(ValueError, match="No date column found"):
            parse_csv_upload(buf)

    def test_non_numeric_close_raises(self):
        buf = BytesIO(b"date,close\n2024-01-01,abc\n2024-01-02,def\n")
        with pytest.raises(ValueError, match="missing value"):
            parse_csv_upload(buf)

    def test_negative_close_raises(self):
        buf = BytesIO(b"date,close\n2024-01-01,-5.0\n2024-01-02,100\n")
        with pytest.raises(ValueError, match="zero or negative"):
            parse_csv_upload(buf)

    def test_duplicate_dates_are_deduplicated(self):
        """Duplicate dates should be removed (keep last)."""
        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
            "close": [100, 101, 102],
        })
        buf = make_csv_bytes(df)
        result = parse_csv_upload(buf)
        assert len(result) == 2  # Dupe removed

    def test_string_path_input(self):
        """Should also accept a file path string."""
        df = make_ohlcv_df(65)
        buf = make_csv_bytes(df)
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as f:
            f.write(buf.getvalue())
            tmp_path = f.name

        try:
            result = parse_csv_upload(tmp_path)
            assert len(result) == 65
        finally:
            os.unlink(tmp_path)


# ============================================================================
# Data validation tests
# ============================================================================


class TestValidateOHLCV:
    """Test validate_ohlcv with various data issues."""

    def test_valid_data_passes(self):
        df = make_ohlcv_df(252)
        result = validate_ohlcv(df)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_none_input(self):
        result = validate_ohlcv(None)
        assert not result.is_valid
        assert "None" in result.errors[0]

    def test_wrong_type_input(self):
        result = validate_ohlcv([1, 2, 3])  # type: ignore
        assert not result.is_valid
        assert "DataFrame" in result.errors[0]

    def test_too_few_rows(self):
        df = make_ohlcv_df(30)
        result = validate_ohlcv(df)
        assert not result.is_valid
        assert any("Insufficient data" in e for e in result.errors)

    def test_exactly_60_rows_passes(self):
        df = make_ohlcv_df(60)
        result = validate_ohlcv(df)
        assert result.is_valid

    def test_negative_close(self):
        df = make_ohlcv_df(100)
        df.loc[df.index[10], "close"] = -5.0
        result = validate_ohlcv(df)
        assert not result.is_valid
        assert any("non-positive" in e for e in result.errors)

    def test_zero_close(self):
        df = make_ohlcv_df(100)
        df.loc[df.index[20], "close"] = 0.0
        result = validate_ohlcv(df)
        assert not result.is_valid

    def test_high_lt_low(self):
        df = make_ohlcv_df(100)
        df.loc[df.index[15], "high"] = 50.0
        df.loc[df.index[15], "low"] = 80.0  # high < low
        result = validate_ohlcv(df)
        assert not result.is_valid
        assert any("high < low" in e for e in result.errors)

    def test_high_lt_close(self):
        df = make_ohlcv_df(100)
        df.loc[df.index[30], "close"] = 200.0
        df.loc[df.index[30], "high"] = 150.0  # high < close
        result = validate_ohlcv(df)
        assert not result.is_valid
        assert any("high < open or close" in e for e in result.errors)

    def test_low_gt_close(self):
        df = make_ohlcv_df(100)
        df.loc[df.index[40], "close"] = 50.0
        df.loc[df.index[40], "low"] = 80.0  # low > close
        result = validate_ohlcv(df)
        assert not result.is_valid
        assert any("low > open or close" in e for e in result.errors)

    def test_duplicate_dates(self):
        df = make_ohlcv_df(100)
        idx = list(df.index)
        idx[5] = idx[3]  # Duplicate
        df.index = pd.DatetimeIndex(idx)
        result = validate_ohlcv(df)
        assert not result.is_valid
        assert any("duplicate" in e for e in result.errors)

    def test_nan_close(self):
        df = make_ohlcv_df(100)
        df.loc[df.index[25], "close"] = np.nan
        result = validate_ohlcv(df)
        assert not result.is_valid
        assert any("NaN" in e for e in result.errors)

    def test_volume_zero_warning(self):
        df = make_ohlcv_df(100)
        df["volume"] = 0
        result = validate_ohlcv(df)
        assert len(result.warnings) > 0
        assert any("zero or negative volume" in w for w in result.warnings)

    def test_missing_close_column(self):
        df = pd.DataFrame({"open": [100, 101, 102]}, index=pd.date_range("2024-01-01", periods=3))
        # Still need enough rows and close column for this test
        dates = pd.date_range("2024-01-01", periods=65, freq="B")
        df = pd.DataFrame({"open": np.linspace(100, 200, 65)}, index=dates)
        result = validate_ohlcv(df)
        assert not result.is_valid
        assert any("close" in e.lower() for e in result.errors)


# ============================================================================
# Data preprocessing tests
# ============================================================================


class TestPreprocessData:
    """Test preprocess_data with filtering and filling."""

    def test_date_range_filter(self):
        df = make_ohlcv_df(252)
        mid_date = df.index[126].strftime("%Y-%m-%d")

        result = preprocess_data(df, start_date=mid_date)
        assert len(result) < len(df)
        assert result.index[0] >= pd.Timestamp(mid_date)

    def test_forward_fill(self):
        """NaN values should be forward-filled."""
        df = make_ohlcv_df(100)
        df.loc[df.index[50], "close"] = np.nan
        df.loc[df.index[51], "close"] = np.nan

        result = preprocess_data(df)
        assert not result["close"].isna().any()

    def test_drop_all_nan_rows(self):
        """Rows where close is NaN after ffill should be dropped."""
        df = make_ohlcv_df(100)
        # Set first 5 closes to NaN (can't ffill from nothing)
        df.loc[df.index[:5], "close"] = np.nan

        result = preprocess_data(df)
        # First rows where close was NaN and had no prior value should be dropped
        assert not result["close"].isna().any()

    def test_empty_after_filter_raises(self):
        df = make_ohlcv_df(100)
        with pytest.raises(ValueError, match="No data remaining"):
            preprocess_data(df, start_date="2099-01-01")

    def test_empty_input_raises(self):
        with pytest.raises(ValueError, match="empty"):
            preprocess_data(pd.DataFrame())

    def test_numeric_conversion(self):
        """String columns should be converted to numeric."""
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        df = pd.DataFrame(
            {
                "open": ["100", "101", "102"] + [str(x) for x in np.linspace(103, 200, 97)],
                "close": [str(x) for x in np.linspace(100, 200, 100)],
            },
            index=dates,
        )

        result = preprocess_data(df)
        assert pd.api.types.is_numeric_dtype(result["close"])
        assert pd.api.types.is_numeric_dtype(result["open"])


# ============================================================================
# Column detection tests
# ============================================================================


class TestDetectColumns:
    """Test _detect_columns helper."""

    def test_standard_columns(self):
        df = pd.DataFrame({
            "Date": ["2024-01-01"],
            "Close": [100.0],
            "Volume": [500000],
        })
        result = _detect_columns(df)
        assert "close" in result.columns
        assert "date" in result.columns
        assert "volume" in result.columns

    def test_partial_match(self):
        """'closing_price' should match the 'closing_price' alias."""
        df = pd.DataFrame({
            "date": ["2024-01-01"],
            "closing_price": [100.0],
        })
        result = _detect_columns(df)
        assert "close" in result.columns


# ============================================================================
# Yahoo Finance tests (mocked)
# ============================================================================


class TestYahooFinance:
    """Test get_yahoo_data with mocked yfinance and Redis."""

    pytestmark = pytest.mark.asyncio

    @pytest.fixture
    def mock_ticker(self):
        """Create a mock yfinance Ticker that returns valid data."""
        dates = pd.date_range("2024-01-01", periods=252, freq="B")
        df = pd.DataFrame(
            {
                "Open": np.linspace(100, 200, 252),
                "High": np.linspace(101, 202, 252),
                "Low": np.linspace(99, 199, 252),
                "Close": np.linspace(100, 200, 252),
                "Volume": np.full(252, 5_000_000),
            },
            index=dates,
        )
        mock = MagicMock()
        mock.history.return_value = df
        return mock

    @pytest.fixture
    def mock_empty_ticker(self):
        mock = MagicMock()
        mock.history.return_value = pd.DataFrame()
        return mock

    # Use module-level patch to mock both yfinance and Redis for all tests
    @pytest.fixture(autouse=True)
    def mock_dependencies(self):
        """Mock yfinance and Redis for all Yahoo tests."""
        from app.services.data_service import _data_cache

        _data_cache._client = None  # Reset singleton between tests

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # Always miss cache

        with patch(
            "yfinance.Ticker"
        ) as mock_yf, patch(
            "redis.asyncio.from_url",
            return_value=mock_redis,
        ):
            yield {"yf": mock_yf, "redis": mock_redis}

    async def test_fetch_valid_ticker(self, mock_dependencies, mock_ticker):
        mock_dependencies["yf"].return_value = mock_ticker

        df = await get_yahoo_data("AAPL", "2024-01-01", "2024-12-31")

        assert isinstance(df, pd.DataFrame)
        assert "close" in df.columns
        assert "open" in df.columns
        assert len(df) == 252

    async def test_empty_result_raises(self, mock_dependencies, mock_empty_ticker):
        mock_dependencies["yf"].return_value = mock_empty_ticker

        with pytest.raises(ValueError, match="No data returned"):
            await get_yahoo_data("INVALID", "2024-01-01", "2024-12-31")

    async def test_invalid_ticker_format_raises(self, mock_dependencies):
        with pytest.raises(ValueError, match="Invalid ticker symbol"):
            await get_yahoo_data("A" * 30, "2024-01-01", "2024-12-31")

    async def test_lowercase_ticker_normalized(self, mock_dependencies, mock_ticker):
        mock_dependencies["yf"].return_value = mock_ticker

        df = await get_yahoo_data("aapl", "2024-01-01", "2024-12-31")
        assert len(df) > 0

    async def test_timeout_raises(self, mock_dependencies, mock_ticker):
        import time

        def slow_history(**kw):
            time.sleep(30)
            return pd.DataFrame()

        mock_ticker.history = slow_history
        mock_dependencies["yf"].return_value = mock_ticker

        with patch("app.services.data_service.API_TIMEOUT", 1.0):
            with pytest.raises(TimeoutError, match="timed out"):
                await get_yahoo_data("AAPL", "2024-01-01", "2024-12-31")

    async def test_cache_hit(self, mock_dependencies, mock_ticker):
        """When Redis returns cached data, yfinance should not be called."""
        dates = pd.date_range("2024-06-01", periods=20, freq="B")
        cached_df = pd.DataFrame(
            {
                "open": np.ones(20) * 100,
                "high": np.ones(20) * 105,
                "low": np.ones(20) * 95,
                "close": np.ones(20) * 102,
                "volume": np.ones(20) * 1000000,
            },
            index=dates,
        )

        # Return cached data from Redis
        import io
        buf = io.BytesIO()
        cached_df.to_parquet(buf, index=True, compression="zstd")
        mock_dependencies["redis"].get.return_value = buf.getvalue()

        df = await get_yahoo_data("AAPL", "2024-01-01", "2024-12-31")

        # Should return cached data
        assert len(df) == 20
        # yfinance should NOT have been called
        mock_dependencies["yf"].assert_not_called()
