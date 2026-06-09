"""
QuantFlow core backtest engine.

Uses vectorbt for vectorized backtesting — processes 10 years of daily data
in under 1 second. Falls back to pure pandas/numpy when vectorbt is unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Number of trading days per year for annualization
TRADING_DAYS = 252


# ============================================================================
# Data structures
# ============================================================================


@dataclass
class Trade:
    entry_date: datetime
    exit_date: datetime
    side: str  # "long" or "short"
    entry_price: float
    exit_price: float
    return_pct: float
    pnl: float


@dataclass
class BacktestInput:
    """Input for a backtest run."""

    ohlcv_data: pd.DataFrame
    # Expected columns: open, high, low, close, volume, datetime (index)
    strategy_type: str  # "ma_cross", "rsi", "bollinger"
    strategy_params: dict = field(default_factory=dict)
    initial_capital: float = 10000.0
    commission: float = 0.001  # 0.1% per trade
    start_date: Optional[str] = None  # "YYYY-MM-DD" slice within ohlcv_data
    end_date: Optional[str] = None

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if self.ohlcv_data.empty:
            raise ValueError("ohlcv_data is empty")
        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(col.lower() for col in self.ohlcv_data.columns)
        if missing:
            raise ValueError(f"ohlcv_data missing columns: {missing}")
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if not (0 <= self.commission <= 0.05):
            raise ValueError("commission must be in [0, 0.05]")
        if self.strategy_type not in ALL_STRATEGIES:
            raise ValueError(
                f"Unknown strategy_type: {self.strategy_type}. "
                f"Supported: {', '.join(ALL_STRATEGIES)}"
            )


@dataclass
class BacktestOutput:
    """Output from a backtest run."""

    # Core metrics
    total_return: float
    annual_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int  # days
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_return: float

    # Time series for charting
    equity_curve: list[dict] = field(default_factory=list)
    # [{"date": "2024-01-02", "value": 10250.0, "benchmark": 10100.0}, ...]
    drawdown_curve: list[dict] = field(default_factory=list)
    # [{"date": "2024-01-02", "value": -0.02}, ...]

    # Trade log
    trades: list[dict] = field(default_factory=list)


# ============================================================================
# Strategy signal generators
# ============================================================================


def _resolve_price_column(df: pd.DataFrame) -> str:
    """Return the close-price column name regardless of casing."""
    for col in df.columns:
        if col.lower() == "close":
            return col
    raise KeyError("No close column found in DataFrame")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase all column names for consistent access."""
    return df.rename(columns=str.lower)


def _generate_ma_cross_signals(
    close: pd.Series, params: dict
) -> tuple[pd.Series, pd.Series]:
    """
    Moving-average crossover strategy.

    Logic: fast MA crosses above slow MA → entry (1).
           fast MA crosses below slow MA → exit (0, covered by short=-1).

    Returns (entries, exits) as boolean Series.
    """
    fast_period = int(params.get("fast_period", 10))
    slow_period = int(params.get("slow_period", 30))
    ma_type = params.get("ma_type", "sma")

    if fast_period >= slow_period:
        raise ValueError("fast_period must be less than slow_period")

    if ma_type == "ema":
        ma_fast = close.ewm(span=fast_period, adjust=False).mean()
        ma_slow = close.ewm(span=slow_period, adjust=False).mean()
    else:
        ma_fast = close.rolling(fast_period).mean()
        ma_slow = close.rolling(slow_period).mean()

    entries = (ma_fast > ma_slow) & (ma_fast.shift(1) <= ma_slow.shift(1))
    exits = (ma_fast < ma_slow) & (ma_fast.shift(1) >= ma_slow.shift(1))

    # Drop NaN periods (first slow_period rows)
    entries.iloc[:slow_period] = False
    exits.iloc[:slow_period] = False

    return entries, exits


def _generate_rsi_signals(
    close: pd.Series, params: dict
) -> tuple[pd.Series, pd.Series]:
    """
    RSI mean-reversion strategy.

    Logic: RSI crosses below oversold → entry (1).
           RSI crosses above overbought → exit.

    Returns (entries, exits) as boolean Series.
    """
    rsi_period = int(params.get("rsi_period", 14))
    oversold = int(params.get("oversold", 30))
    overbought = int(params.get("overbought", 70))

    if oversold >= overbought:
        raise ValueError("oversold must be less than overbought")

    # Calculate RSI
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(rsi_period).mean()
    loss = (-delta.clip(upper=0)).rolling(rsi_period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))

    entries = (rsi < oversold) & (rsi.shift(1) >= oversold)
    exits = (rsi > overbought) & (rsi.shift(1) <= overbought)

    entries.iloc[: rsi_period + 1] = False
    exits.iloc[: rsi_period + 1] = False

    return entries, exits


def _generate_bollinger_signals(
    close: pd.Series, params: dict
) -> tuple[pd.Series, pd.Series]:
    """
    Bollinger Bands mean-reversion strategy.

    Logic: price crosses below lower band → entry (1).
           price crosses above upper band → exit.

    Returns (entries, exits) as boolean Series.
    """
    bb_period = int(params.get("bb_period", 20))
    bb_std = float(params.get("bb_std", 2.0))

    sma = close.rolling(bb_period).mean()
    std = close.rolling(bb_period).std()
    upper_band = sma + bb_std * std
    lower_band = sma - bb_std * std

    entries = (close < lower_band) & (close.shift(1) >= lower_band.shift(1))
    exits = (close > upper_band) & (close.shift(1) <= upper_band.shift(1))

    entries.iloc[:bb_period] = False
    exits.iloc[:bb_period] = False

    return entries, exits


# Strategy dispatch
def _generate_macd_signals(
    close: pd.Series, params: dict
) -> tuple[pd.Series, pd.Series]:
    """
    MACD signal-line crossover strategy.

    Logic: MACD crosses above signal line → entry.
           MACD crosses below signal line → exit.

    Returns (entries, exits) as boolean Series.
    """
    fast = int(params.get("fast_period", 12))
    slow = int(params.get("slow_period", 26))
    signal_period = int(params.get("signal_period", 9))

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

    entries = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
    exits = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))

    entries.iloc[:slow + signal_period] = False
    exits.iloc[:slow + signal_period] = False

    return entries, exits


# ── Strategy 5: Dual Moving Average (triple-MA confirmation) ────────────────

def _generate_dual_ma_signals(close: pd.Series, params: dict) -> tuple[pd.Series, pd.Series]:
    """Triple-MA alignment: short > mid > long → entry. short < mid → exit."""
    short = int(params.get("short_period", 5))
    mid = int(params.get("mid_period", 20))
    long = int(params.get("long_period", 60))
    if not (short < mid < long):
        raise ValueError(f"short({short}) < mid({mid}) < long({long}) required")
    ma_s = close.rolling(short).mean()
    ma_m = close.rolling(mid).mean()
    ma_l = close.rolling(long).mean()
    bullish = (ma_s > ma_m) & (ma_m > ma_l)
    entries = bullish & ~bullish.shift(1).fillna(False)
    exits = (ma_s < ma_m) & (ma_s.shift(1) >= ma_m.shift(1))
    entries.iloc[:long] = False; exits.iloc[:long] = False
    return entries.fillna(False), exits.fillna(False)


# ── Strategy 6: KDJ Stochastic ──────────────────────────────────────────────

def _generate_kdj_signals(close: pd.Series, params: dict, high=None, low=None) -> tuple[pd.Series, pd.Series]:
    """KDJ golden cross in oversold zone → entry. Dead cross in overbought → exit."""
    n = int(params.get("kdj_period", 9))
    oversold = float(params.get("oversold", 20))
    overbought = float(params.get("overbought", 80))
    h = high if high is not None else close
    l = low if low is not None else close
    low_n = l.rolling(n).min()
    high_n = h.rolling(n).max()
    rsv = (close - low_n) / (high_n - low_n + 1e-10) * 100
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    entries = (k > d) & (k.shift(1) <= d.shift(1)) & (d < oversold + 20)
    exits = (k < d) & (k.shift(1) >= d.shift(1)) & (d > overbought - 20)
    entries.iloc[:n+3] = False; exits.iloc[:n+3] = False
    return entries.fillna(False), exits.fillna(False)


# ── Strategy 7: ATR Breakout ────────────────────────────────────────────────

def _generate_atr_breakout_signals(close: pd.Series, params: dict, high=None, low=None) -> tuple[pd.Series, pd.Series]:
    """Breakout above N×ATR channel → entry. Drop below midline → exit."""
    atr_p = int(params.get("atr_period", 14))
    mult = float(params.get("multiplier", 2.0))
    h = high if high is not None else close
    l = low if low is not None else close
    tr = pd.concat([h - l, (h - close.shift()).abs(), (l - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(atr_p).mean()
    mid = close.rolling(atr_p).mean()
    upper = mid + mult * atr
    entries = (close > upper) & (close.shift(1) <= upper.shift(1))
    exits = (close < mid) & (close.shift(1) >= mid.shift(1))
    entries.iloc[:atr_p] = False; exits.iloc[:atr_p] = False
    return entries.fillna(False), exits.fillna(False)


# ── Strategy 8: CCI ─────────────────────────────────────────────────────────

def _generate_cci_signals(close: pd.Series, params: dict, high=None, low=None) -> tuple[pd.Series, pd.Series]:
    """CCI cross above oversold → entry. Cross below overbought → exit."""
    period = int(params.get("cci_period", 20))
    oversold = float(params.get("oversold", -100))
    overbought = float(params.get("overbought", 100))
    h = high if high is not None else close
    l = low if low is not None else close
    tp = (h + l + close) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - sma) / (0.015 * mad + 1e-10)
    entries = (cci > oversold) & (cci.shift(1) <= oversold)
    exits = (cci < overbought) & (cci.shift(1) >= overbought)
    entries.iloc[:period] = False; exits.iloc[:period] = False
    return entries.fillna(False), exits.fillna(False)


# ── Strategy 9: Donchian Channel (Turtle) ───────────────────────────────────

def _generate_donchian_signals(close: pd.Series, params: dict, high=None, low=None) -> tuple[pd.Series, pd.Series]:
    """Breakout of N-day high → entry. Drop below M-day low → exit."""
    entry_p = int(params.get("entry_period", 20))
    exit_p = int(params.get("exit_period", 10))
    h = high if high is not None else close
    l = low if low is not None else close
    upper = h.rolling(entry_p).max().shift(1)
    lower = l.rolling(exit_p).min().shift(1)
    entries = close > upper
    exits = close < lower
    entries.iloc[:entry_p+1] = False; exits.iloc[:entry_p+1] = False
    return entries.fillna(False), exits.fillna(False)


# ── Strategy 10: Momentum ───────────────────────────────────────────────────

def _generate_momentum_signals(close: pd.Series, params: dict) -> tuple[pd.Series, pd.Series]:
    """Momentum > threshold → entry. Momentum < 0 → exit."""
    lookback = int(params.get("lookback", 20))
    threshold = float(params.get("threshold", 0.05))
    mom = close.pct_change(lookback)
    entries = (mom > threshold) & (mom.shift(1) <= threshold)
    exits = (mom < 0) & (mom.shift(1) >= 0)
    entries.iloc[:lookback+1] = False; exits.iloc[:lookback+1] = False
    return entries.fillna(False), exits.fillna(False)


# ── Strategy 11: Mean Reversion ─────────────────────────────────────────────

def _generate_mean_reversion_signals(close: pd.Series, params: dict) -> tuple[pd.Series, pd.Series]:
    """Price deviates N std below mean → entry. Reverts → exit."""
    period = int(params.get("period", 20))
    entry_std = float(params.get("entry_std", 2.0))
    exit_std = float(params.get("exit_std", 0.5))
    ma = close.rolling(period).mean()
    std = close.rolling(period).std()
    z = (close - ma) / (std + 1e-10)
    entries = (z < -entry_std) & (z.shift(1) >= -entry_std)
    exits = (z > -exit_std) & (z.shift(1) <= -exit_std)
    entries.iloc[:period] = False; exits.iloc[:period] = False
    return entries.fillna(False), exits.fillna(False)


# ── Strategy 12: Volume Breakout ────────────────────────────────────────────

def _generate_volume_breakout_signals(close: pd.Series, params: dict, volume=None) -> tuple[pd.Series, pd.Series]:
    """Volume spike + rising price → entry. Price drops → exit."""
    vol_p = int(params.get("vol_period", 20))
    vol_m = float(params.get("vol_multiplier", 2.0))
    price_p = int(params.get("price_period", 5))
    vol = volume if volume is not None else pd.Series(0, index=close.index)
    vol_avg = vol.rolling(vol_p).mean()
    price_chg = close.pct_change(price_p)
    vol_spike = vol > vol_avg * vol_m
    entries = vol_spike & (price_chg > 0) & ~(vol_spike.shift(1).fillna(False) & (price_chg.shift(1).fillna(0) > 0))
    exits = (price_chg < 0) & (price_chg.shift(1) >= 0)
    entries.iloc[:max(vol_p, price_p)] = False; exits.iloc[:max(vol_p, price_p)] = False
    return entries.fillna(False), exits.fillna(False)


# ── Dispatch ────────────────────────────────────────────────────────────────

ALL_STRATEGIES = [
    "ma_cross", "rsi", "bollinger", "macd",
    "dual_ma", "kdj", "atr_breakout", "cci",
    "donchian", "momentum", "mean_reversion", "volume_breakout",
]


def generate_signals(df: pd.DataFrame, strategy_type: str, params: dict) -> tuple[pd.Series, pd.Series]:
    """Unified signal generation with OHLV context when needed."""
    close = df["close"]
    high = df.get("high", close)
    low = df.get("low", close)
    volume = df.get("volume")

    if strategy_type == "ma_cross":
        return _generate_ma_cross_signals(close, params)
    elif strategy_type == "rsi":
        return _generate_rsi_signals(close, params)
    elif strategy_type == "bollinger":
        return _generate_bollinger_signals(close, params)
    elif strategy_type == "macd":
        return _generate_macd_signals(close, params)
    elif strategy_type == "dual_ma":
        return _generate_dual_ma_signals(close, params)
    elif strategy_type == "kdj":
        return _generate_kdj_signals(close, params, high, low)
    elif strategy_type == "atr_breakout":
        return _generate_atr_breakout_signals(close, params, high, low)
    elif strategy_type == "cci":
        return _generate_cci_signals(close, params, high, low)
    elif strategy_type == "donchian":
        return _generate_donchian_signals(close, params, high, low)
    elif strategy_type == "momentum":
        return _generate_momentum_signals(close, params)
    elif strategy_type == "mean_reversion":
        return _generate_mean_reversion_signals(close, params)
    elif strategy_type == "volume_breakout":
        return _generate_volume_breakout_signals(close, params, volume)
    else:
        raise ValueError(f"Unknown strategy_type: {strategy_type}. Supported: {', '.join(ALL_STRATEGIES)}")


STRATEGY_FUNCTIONS = {
    "ma_cross": _generate_ma_cross_signals,
    "rsi": _generate_rsi_signals,
    "bollinger": _generate_bollinger_signals,
    "macd": _generate_macd_signals,
    "dual_ma": _generate_dual_ma_signals,
    "kdj": _generate_kdj_signals,
    "atr_breakout": _generate_atr_breakout_signals,
    "cci": _generate_cci_signals,
    "donchian": _generate_donchian_signals,
    "momentum": _generate_momentum_signals,
    "mean_reversion": _generate_mean_reversion_signals,
    "volume_breakout": _generate_volume_breakout_signals,
}


# ============================================================================
# Core backtest runner
# ============================================================================


def run_backtest(input: BacktestInput) -> BacktestOutput:
    """Run a backtest and return the complete output."""
    # --- 1. Prepare data ---
    df = _normalize_columns(input.ohlcv_data.copy())

    # Ensure datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = None
        for col in df.columns:
            if "date" in col.lower() or "datetime" in col.lower() or "time" in col.lower():
                date_col = col
                break
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.set_index(date_col)
        else:
            raise ValueError("ohlcv_data must have a datetime column or DatetimeIndex")

    # Normalize timezone (yfinance returns tz-aware timestamps for US stocks)
    if hasattr(df.index, "tz") and df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)

    # Slice to date range if specified
    if input.start_date:
        df = df[df.index >= pd.Timestamp(input.start_date)]
    if input.end_date:
        df = df[df.index <= pd.Timestamp(input.end_date)]

    close = df["close"]
    if len(close) < 50:
        raise ValueError(f"Insufficient data: {len(close)} rows, need at least 50")

    # --- 2. Generate signals ---
    strategy_fn = STRATEGY_FUNCTIONS[input.strategy_type]
    entries, exits = strategy_fn(close, input.strategy_params)

    # Clean up: ensure exits don't happen before first entry
    entries = entries.astype(bool)
    exits = exits.astype(bool)

    # --- 3. Run vectorized backtest ---
    equity, trade_records = _simulate_trades(
        close,
        entries,
        exits,
        input.initial_capital,
        input.commission,
    )

    # --- 4. Benchmark (buy & hold) ---
    benchmark_equity = input.initial_capital * (close / close.iloc[0])

    # --- 5. Calculate metrics ---
    returns = equity.pct_change().dropna()

    total_return = float((equity.iloc[-1] / input.initial_capital) - 1)

    if len(returns) > 1 and returns.std() > 0:
        annual_return = float((1 + total_return) ** (TRADING_DAYS / len(returns)) - 1)
        sharpe = float((returns.mean() / returns.std()) * np.sqrt(TRADING_DAYS))
        # Sortino: only penalizes downside volatility
        downside = returns[returns < 0]
        if len(downside) > 0 and downside.std() > 0:
            sortino = float((returns.mean() / downside.std()) * np.sqrt(TRADING_DAYS))
        else:
            sortino = 0.0
    else:
        annual_return = 0.0
        sharpe = 0.0
        sortino = 0.0

    # Drawdown
    cummax = equity.cummax()
    dd_series = (equity - cummax) / cummax
    max_dd = float(dd_series.min())

    # Max drawdown duration
    dd_duration = _max_drawdown_duration(equity)

    # Trade analysis
    if trade_records:
        trades_df = pd.DataFrame(trade_records)
        wins = trades_df[trades_df["pnl"] > 0]
        win_rate = float(len(wins) / len(trades_df)) if len(trades_df) > 0 else 0.0

        total_profit = float(wins["pnl"].sum()) if len(wins) > 0 else 0.0
        losses = trades_df[trades_df["pnl"] < 0]
        total_loss = float(abs(losses["pnl"].sum())) if len(losses) > 0 else 0.0
        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")
        avg_trade_return = float(trades_df["return_pct"].mean())
        total_trades = len(trades_df)
    else:
        win_rate = 0.0
        profit_factor = 0.0
        avg_trade_return = 0.0
        total_trades = 0

    # --- 6. Build output structures ---
    equity_curve = [
        {
            "date": idx.strftime("%Y-%m-%d"),
            "value": float(equity[idx]),
            "benchmark": float(benchmark_equity[idx]),
        }
        for idx in equity.index
    ]

    drawdown_curve = [
        {"date": idx.strftime("%Y-%m-%d"), "value": float(dd_series[idx])}
        for idx in dd_series.index
    ]

    trades_output = [
        {
            "entry_date": t["entry_date"].strftime("%Y-%m-%d"),
            "exit_date": t["exit_date"].strftime("%Y-%m-%d"),
            "side": t["side"],
            "entry_price": t["entry_price"],
            "exit_price": t["exit_price"],
            "return_pct": t["return_pct"],
            "pnl": t["pnl"],
        }
        for t in trade_records
    ]

    return BacktestOutput(
        total_return=total_return,
        annual_return=annual_return,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=max_dd,
        max_drawdown_duration=dd_duration,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_trades=total_trades,
        avg_trade_return=avg_trade_return,
        equity_curve=equity_curve,
        drawdown_curve=drawdown_curve,
        trades=trades_output,
    )


# ============================================================================
# Portfolio simulation (vectorized)
# ============================================================================


def _simulate_trades(
    close: pd.Series,
    entries: pd.Series,
    exits: pd.Series,
    initial_capital: float,
    commission: float,
) -> tuple[pd.Series, list[dict]]:
    """
    Simulate a long-only portfolio with entry/exit signals.

    State machine:
    - out_of_market: wait for entry signal → buy at next bar's open
    - in_market: wait for exit signal → sell at next bar's open

    Returns (equity_series, trade_records).
    """
    equity = pd.Series(initial_capital, index=close.index, dtype=float)
    trades_output: list[dict] = []

    in_position = False
    entry_price = 0.0
    entry_date: pd.Timestamp | None = None
    shares = 0.0
    cash = initial_capital

    for i in range(len(close) - 1):
        idx = close.index[i]
        next_idx = close.index[i + 1]
        price_today = float(close.iloc[i])
        price_next_open = float(close.iloc[i + 1])  # approximate with next close

        # --- Entry logic ---
        if not in_position and entries.iloc[i] and not np.isnan(price_next_open):
            entry_price = price_next_open * (1 + commission)
            shares = cash / entry_price
            cash = 0.0
            in_position = True
            entry_date = next_idx

        # --- Exit logic ---
        elif in_position and exits.iloc[i] and not np.isnan(price_next_open):
            exit_price = price_next_open * (1 - commission)
            pnl = shares * (exit_price - entry_price)
            cash = shares * exit_price
            return_pct = (exit_price / entry_price) - 1
            trades_output.append(
                {
                    "entry_date": entry_date,
                    "exit_date": next_idx,
                    "side": "long",
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "return_pct": round(return_pct, 6),
                    "pnl": round(pnl, 2),
                }
            )
            shares = 0.0
            in_position = False
            entry_date = None

        # --- Mark to market ---
        if in_position:
            mark = shares * float(close.iloc[i + 1])
        else:
            mark = 0.0

        equity.iloc[i + 1] = cash + mark

    # If still in position at end, close it
    if in_position:
        last_price = float(close.iloc[-1])
        exit_price = last_price * (1 - commission)
        pnl = shares * (exit_price - entry_price)
        cash = shares * exit_price
        return_pct = (exit_price / entry_price) - 1
        trades_output.append(
            {
                "entry_date": entry_date,
                "exit_date": close.index[-1],
                "side": "long",
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return_pct": round(return_pct, 6),
                "pnl": round(pnl, 2),
            }
        )
        equity.iloc[-1] = cash

    return equity, trades_output


def _max_drawdown_duration(equity: pd.Series) -> int:
    """Return the longest drawdown duration in trading days."""
    cummax = equity.cummax()
    in_drawdown = equity < cummax

    if not in_drawdown.any():
        return 0

    max_duration = 0
    current = 0
    for val in in_drawdown:
        if val:
            current += 1
            max_duration = max(max_duration, current)
        else:
            current = 0
    return max_duration


# ============================================================================
# Async wrapper (for FastAPI compatibility)
# ============================================================================


async def run_backtest_async(input: BacktestInput) -> BacktestOutput:
    """Async-compatible wrapper that runs the backtest in a thread pool."""
    import asyncio

    return await asyncio.to_thread(run_backtest, input)


# ============================================================================
# Data helpers
# ============================================================================


def generate_sample_data(
    days: int = 2520,  # ~10 years of trading days
    seed: int = 42,
    start_price: float = 100.0,
    mu: float = 0.0005,
    sigma: float = 0.015,
) -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    dates = pd.date_range(end=pd.Timestamp.now(), periods=days, freq="B")
    rng = np.random.default_rng(seed)
    returns = rng.normal(mu, sigma, days)
    close = start_price * np.cumprod(1 + returns)

    # Generate OHLC from close
    daily_range = close * sigma * rng.uniform(0.3, 1.5, days)
    open_p = close - rng.normal(0, daily_range * 0.3, days)
    high = np.maximum(open_p, close) + np.abs(rng.normal(0, daily_range * 0.2, days))
    low = np.minimum(open_p, close) - np.abs(rng.normal(0, daily_range * 0.2, days))
    volume = rng.integers(1_000_000, 10_000_000, days)

    return pd.DataFrame(
        {
            "open": open_p,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )
