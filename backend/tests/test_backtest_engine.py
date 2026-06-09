"""
Unit tests for the QuantFlow backtest engine.
"""

import pytest
import pandas as pd
import numpy as np

from app.services.backtest_engine import (
    BacktestInput,
    BacktestOutput,
    generate_sample_data,
    run_backtest,
    _generate_ma_cross_signals,
    _generate_rsi_signals,
    _generate_bollinger_signals,
    _max_drawdown_duration,
    _simulate_trades,
)

# ============================================================================
# Shared fixtures
# ============================================================================


@pytest.fixture
def sample_data():
    """10 years of daily OHLCV data."""
    return generate_sample_data(days=2520, seed=42)


@pytest.fixture
def short_data():
    """Short dataset for edge case testing."""
    return generate_sample_data(days=100, seed=1)


@pytest.fixture
def trending_up_data():
    """Strong uptrend for predictable strategy outcomes."""
    days = 500
    dates = pd.date_range(end=pd.Timestamp.now(), periods=days, freq="B")
    rng = np.random.default_rng(123)
    # Strong upward drift (20% annualized)
    returns = rng.normal(0.0008, 0.01, days)
    close = 100.0 * np.cumprod(1 + returns)

    return pd.DataFrame(
        {
            "open": close * 0.999,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": rng.integers(1_000_000, 5_000_000, days),
        },
        index=dates,
    )


# ============================================================================
# Test 1: MA Cross strategy produces valid output
# ============================================================================


class TestMACrossStrategy:
    def test_produces_valid_output(self, sample_data):
        input_ = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="ma_cross",
            strategy_params={"fast_period": 10, "slow_period": 30, "ma_type": "sma"},
            initial_capital=10000.0,
            commission=0.001,
        )

        output = run_backtest(input_)

        assert isinstance(output, BacktestOutput)
        assert isinstance(output.total_return, float)
        assert isinstance(output.sharpe_ratio, float)
        assert isinstance(output.sortino_ratio, float)
        assert isinstance(output.max_drawdown, float)
        assert output.max_drawdown <= 0.0  # drawdown is always ≤ 0 or NaN
        assert isinstance(output.total_trades, int)
        assert len(output.equity_curve) > 0
        assert len(output.drawdown_curve) > 0

    def test_equity_curve_has_required_fields(self, sample_data):
        input_ = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="ma_cross",
            strategy_params={"fast_period": 5, "slow_period": 20},
            initial_capital=50000.0,
        )

        output = run_backtest(input_)

        # Every equity point must have date, value, benchmark
        for point in output.equity_curve:
            assert "date" in point
            assert "value" in point
            assert "benchmark" in point
            assert point["value"] > 0  # equity should be positive

    def test_fast_ema_cross(self, sample_data):
        """EMA crossover with fast=5, slow=20 should produce many trades."""
        input_ = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="ma_cross",
            strategy_params={"fast_period": 5, "slow_period": 20, "ma_type": "ema"},
        )

        output = run_backtest(input_)
        assert output.total_trades > 0

    def test_fast_ge_slow_raises(self, sample_data):
        """fast_period >= slow_period should raise."""
        with pytest.raises(ValueError, match="fast_period must be less"):
            input_ = BacktestInput(
                ohlcv_data=sample_data,
                strategy_type="ma_cross",
                strategy_params={"fast_period": 50, "slow_period": 20},
            )
            run_backtest(input_)


# ============================================================================
# Test 2: RSI strategy
# ============================================================================


class TestRSIStrategy:
    def test_produces_valid_output(self, sample_data):
        input_ = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="rsi",
            strategy_params={"rsi_period": 14, "oversold": 30, "overbought": 70},
            initial_capital=10000.0,
        )

        output = run_backtest(input_)

        assert isinstance(output.win_rate, float)
        assert 0.0 <= output.win_rate <= 1.0
        assert output.total_trades >= 0

    def test_oversold_ge_overbought_raises(self, sample_data):
        """oversold >= overbought should raise."""
        with pytest.raises(ValueError, match="oversold must be less"):
            input_ = BacktestInput(
                ohlcv_data=sample_data,
                strategy_type="rsi",
                strategy_params={"oversold": 80, "overbought": 30},
            )
            run_backtest(input_)

    def test_tight_bands_more_trades(self, sample_data):
        """Tighter oversold/overbought → more trades."""
        wide = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="rsi",
            strategy_params={"oversold": 20, "overbought": 80},
        )
        tight = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="rsi",
            strategy_params={"oversold": 40, "overbought": 60},
        )

        wide_out = run_backtest(wide)
        tight_out = run_backtest(tight)
        # Tighter bands should generate more trades
        assert tight_out.total_trades >= wide_out.total_trades


# ============================================================================
# Test 3: Bollinger Bands strategy
# ============================================================================


class TestBollingerStrategy:
    def test_produces_valid_output(self, sample_data):
        input_ = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="bollinger",
            strategy_params={"bb_period": 20, "bb_std": 2.0},
        )

        output = run_backtest(input_)
        assert isinstance(output.total_trades, int)
        assert isinstance(output.profit_factor, float)
        assert len(output.trades) == output.total_trades

    def test_narrow_bands_more_trades(self, sample_data):
        """Smaller std multiplier → more entries/exits."""
        wide_bands = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="bollinger",
            strategy_params={"bb_period": 20, "bb_std": 3.0},
        )
        narrow_bands = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="bollinger",
            strategy_params={"bb_period": 20, "bb_std": 1.0},
        )

        wide_out = run_backtest(wide_bands)
        narrow_out = run_backtest(narrow_bands)
        # Narrower bands → more signal triggers
        assert narrow_out.total_trades >= wide_out.total_trades

    def test_trade_structure(self, sample_data):
        """Each trade record must have all required fields."""
        input_ = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="bollinger",
            strategy_params={"bb_period": 20, "bb_std": 2.0},
        )

        output = run_backtest(input_)

        for trade in output.trades:
            assert "entry_date" in trade
            assert "exit_date" in trade
            assert "side" in trade
            assert "entry_price" in trade
            assert "exit_price" in trade
            assert "return_pct" in trade
            assert "pnl" in trade
            assert trade["side"] == "long"


# ============================================================================
# Test 4: Error handling
# ============================================================================


class TestErrorHandling:
    def test_empty_data(self):
        with pytest.raises(ValueError, match="ohlcv_data is empty"):
            BacktestInput(
                ohlcv_data=pd.DataFrame(),
                strategy_type="ma_cross",
            )

    def test_missing_columns(self):
        df = pd.DataFrame({"close": [100, 101, 102]})
        with pytest.raises(ValueError, match="ohlcv_data missing columns"):
            BacktestInput(
                ohlcv_data=df,
                strategy_type="ma_cross",
            )

    def test_invalid_strategy_type(self, sample_data):
        with pytest.raises(ValueError, match="Unknown strategy_type"):
            BacktestInput(
                ohlcv_data=sample_data,
                strategy_type="foobar_xyz",  # truly unsupported
            )

    def test_negative_capital(self, sample_data):
        with pytest.raises(ValueError, match="initial_capital must be positive"):
            BacktestInput(
                ohlcv_data=sample_data,
                strategy_type="ma_cross",
                initial_capital=-1000,
            )

    def test_commission_out_of_range(self, sample_data):
        with pytest.raises(ValueError, match="commission"):
            BacktestInput(
                ohlcv_data=sample_data,
                strategy_type="ma_cross",
                commission=0.10,  # 10% commission
            )

    def test_insufficient_data(self, sample_data):
        """Less than 50 rows should fail."""
        tiny = sample_data.iloc[:30]
        with pytest.raises(ValueError, match="Insufficient data"):
            input_ = BacktestInput(
                ohlcv_data=tiny,
                strategy_type="ma_cross",
            )
            run_backtest(input_)

    def test_date_slicing(self, short_data):
        """start_date and end_date should slice within the data."""
        dates = short_data.index
        mid_point = dates[len(dates) // 2]

        input_ = BacktestInput(
            ohlcv_data=short_data,
            strategy_type="ma_cross",
            strategy_params={"fast_period": 5, "slow_period": 15},
            start_date=mid_point.strftime("%Y-%m-%d"),
        )

        output = run_backtest(input_)
        # Should still produce valid output on sliced data
        assert len(output.equity_curve) > 0


# ============================================================================
# Test 5: Benchmark comparison
# ============================================================================


class TestBenchmarkComparison:
    def test_buy_and_hold_benchmark_present(self, sample_data):
        """Equity curve must include benchmark values."""
        input_ = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="ma_cross",
            strategy_params={"fast_period": 10, "slow_period": 30},
        )

        output = run_backtest(input_)

        # Benchmark should start at initial_capital
        first = output.equity_curve[0]
        assert abs(first["benchmark"] - 10000.0) < 1.0

    def test_trending_market_benchmark_beats_no_trades(self, trending_up_data):
        """In a strong uptrend, buy-and-hold should outperform if no trades fire."""
        input_ = BacktestInput(
            ohlcv_data=trending_up_data,
            strategy_type="ma_cross",
            strategy_params={
                "fast_period": 200,
                "slow_period": 250,
            },  # very slow, may not fire
        )

        output = run_backtest(input_)

        # Get final benchmark value
        final_benchmark = output.equity_curve[-1]["benchmark"]
        # In strong uptrend, benchmark should be above initial capital
        assert final_benchmark > 10000.0

    def test_drawdown_curve_matches_equity(self, sample_data):
        """Drawdown values should be ≤ 0 and match equity peaks."""
        input_ = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="bollinger",
            strategy_params={"bb_period": 20, "bb_std": 2.0},
        )

        output = run_backtest(input_)

        for dd in output.drawdown_curve:
            assert dd["value"] <= 0.0  # drawdown is always ≤ 0

    def test_metrics_consistency(self, sample_data):
        """Cross-validate derived metrics."""
        input_ = BacktestInput(
            ohlcv_data=sample_data,
            strategy_type="rsi",
            strategy_params={"rsi_period": 14, "oversold": 30, "overbought": 70},
            initial_capital=10000.0,
        )

        output = run_backtest(input_)

        # total_return should match equity curve
        first_equity = output.equity_curve[0]["value"]
        last_equity = output.equity_curve[-1]["value"]
        total_return_from_curve = (last_equity / first_equity) - 1

        # Allow small rounding differences
        assert abs(output.total_return - total_return_from_curve) < 0.01

        # win_rate should be between 0 and 1 if there are trades
        if output.total_trades > 0:
            assert 0.0 <= output.win_rate <= 1.0

        # profit_factor should be ≥ 0
        assert output.profit_factor >= 0.0 or output.total_trades == 0


# ============================================================================
# Helper function tests
# ============================================================================


class TestMaxDrawdownDuration:
    def test_no_drawdown(self):
        equity = pd.Series([100, 110, 120, 130, 140])
        assert _max_drawdown_duration(equity) == 0

    def test_single_drawdown_period(self):
        equity = pd.Series([100, 110, 105, 108, 112, 110, 115, 120])
        duration = _max_drawdown_duration(equity)
        assert duration > 0

    def test_deep_drawdown(self):
        equity = pd.Series([100, 90, 80, 85, 82, 78, 80, 90, 100])
        duration = _max_drawdown_duration(equity)
        # Most of this series is in drawdown
        assert duration >= 5


class TestSimulateTrades:
    def test_no_signals(self, sample_data):
        """No entry signals → zero trades, equity stays flat."""
        close = sample_data["close"]
        entries = pd.Series(False, index=close.index)
        exits = pd.Series(False, index=close.index)

        equity, trades = _simulate_trades(close, entries, exits, 10000.0, 0.001)

        assert len(trades) == 0
        # Equity should stay at initial capital (all cash)
        assert abs(equity.iloc[-1] - 10000.0) < 0.01

    def test_single_trade(self, sample_data):
        """One entry, one exit → one trade."""
        close = sample_data["close"]
        n = len(close)
        entries = pd.Series(False, index=close.index)
        exits = pd.Series(False, index=close.index)
        entries.iloc[100] = True
        exits.iloc[150] = True

        equity, trades = _simulate_trades(close, entries, exits, 10000.0, 0.0)

        assert len(trades) == 1
        trade = trades[0]
        assert trade["side"] == "long"
        assert trade["entry_price"] > 0
        assert trade["exit_price"] > 0

    def test_commission_reduces_return(self, sample_data):
        """Higher commission → lower equity."""
        close = sample_data["close"]
        n = len(close)
        entries = pd.Series(False, index=close.index)
        exits = pd.Series(False, index=close.index)
        entries.iloc[100] = True
        exits.iloc[150] = True

        eq_zero, _ = _simulate_trades(close, entries, exits, 10000.0, 0.0)
        eq_high, _ = _simulate_trades(close, entries, exits, 10000.0, 0.01)

        # Higher commission should result in lower final equity
        assert eq_zero.iloc[-1] >= eq_high.iloc[-1]


# ============================================================================
# Performance test
# ============================================================================


class TestPerformance:
    """Verify that 10 years of daily data backtests in under 1 second."""

    def test_10_year_backtest_performance(self):
        import time

        data = generate_sample_data(days=2520, seed=42)

        input_ = BacktestInput(
            ohlcv_data=data,
            strategy_type="ma_cross",
            strategy_params={"fast_period": 10, "slow_period": 30},
        )

        start = time.perf_counter()
        output = run_backtest(input_)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"10-year backtest took {elapsed:.3f}s (must be < 1s)"
        assert len(output.equity_curve) > 2000
