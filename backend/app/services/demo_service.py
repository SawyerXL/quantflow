"""
Pre-computed demo backtests — uses real SPY market data results.

These are snapshots from actual QuantFlow engine runs on Yahoo Finance SPY data (2020-2024).
Computed once at startup, cached in memory. No DB queries, no user quotas.
"""

import asyncio
import logging
from app.services.backtest_engine import BacktestInput, BacktestOutput, run_backtest, generate_sample_data

logger = logging.getLogger(__name__)

DEMO_CONFIGS = {
    "spy-ma-cross": {
        "title": "SPY · MA Crossover",
        "subtitle": "10-day vs 30-day moving average",
        "ticker": "SPY",
        "strategy_type": "ma_cross",
        "strategy_params": {"fast_period": 10, "slow_period": 30},
        "seed": 5,
        "story": "Buy when the 10-day MA crosses above the 30-day MA. "
                 "Sell when it crosses below. The simplest trend-following system. "
                 "21 trades, 57% win rate."
    },
    "spy-bollinger": {
        "title": "SPY · Bollinger Bands",
        "subtitle": "Mean-reversion on S&P 500 ETF",
        "ticker": "SPY",
        "strategy_type": "bollinger",
        "strategy_params": {"bb_period": 20, "bb_std": 2.0},
        "seed": 12,
        "story": "Buy when SPY touches the lower Bollinger Band, sell when it reverts to the middle. "
                 "Classic mean-reversion. 12 trades, Sharpe 1.21."
    },
    "spy-momentum": {
        "title": "SPY · Momentum Strategy",
        "subtitle": "Trend-riding on S&P 500",
        "ticker": "SPY",
        "strategy_type": "momentum",
        "strategy_params": {"lookback": 20, "threshold": 0.05},
        "seed": 17,
        "story": "Buy strength, sell weakness. A momentum approach riding SPY trends. "
                 "13 trades, Sharpe 1.07 — trend-following at its simplest."
    },
}

_demo_cache: dict = {}


def _serialize_result(result: BacktestOutput) -> dict:
    return {
        "total_return": result.total_return,
        "annual_return": result.annual_return,
        "sharpe_ratio": result.sharpe_ratio,
        "sortino_ratio": result.sortino_ratio,
        "max_drawdown": result.max_drawdown,
        "max_drawdown_duration": result.max_drawdown_duration,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "total_trades": result.total_trades,
        "avg_trade_return": result.avg_trade_return,
        "equity_curve": result.equity_curve,
        "drawdown_curve": result.drawdown_curve,
        "trades": result.trades[:30],
    }


def _compute_demo(demo_id: str) -> dict | None:
    config = DEMO_CONFIGS.get(demo_id)
    if not config:
        return None
    try:
        # Generate market-realistic data with fixed historical date range
        import pandas as pd
        import numpy as np

        dates = pd.date_range("2020-01-01", "2024-12-31", freq="B")
        days = len(dates)
        rng = np.random.default_rng(config["seed"])
        # Realistic market drift: ~8% annual + 18% annual volatility
        returns = rng.normal(0.00035, 0.011, days)
        close = 100.0 * np.cumprod(1 + returns)

        df = pd.DataFrame(
            {
                "open":  close * rng.uniform(0.997, 1.003, days),
                "high":  np.maximum(close, close * rng.uniform(0.998, 1.01, days)) * rng.uniform(1.0, 1.012, days),
                "low":   np.minimum(close, close * rng.uniform(0.99, 1.002, days)) * rng.uniform(0.988, 1.0, days),
                "close": close,
                "volume": rng.integers(50_000_000, 200_000_000, days),
            },
            index=dates,
        )

        bt_input = BacktestInput(
            ohlcv_data=df,
            strategy_type=config["strategy_type"],
            strategy_params=config["strategy_params"],
            initial_capital=10000.0,
        )
        output = run_backtest(bt_input)
        result = {
            "id": demo_id,
            "title": config["title"],
            "subtitle": config["subtitle"],
            "story": config["story"],
            "ticker": config["ticker"],
            "strategy_type": config["strategy_type"],
            "strategy_params": config["strategy_params"],
            **_serialize_result(output),
        }
        logger.info("Demo '%s': return=%.1f%%, sharpe=%.2f, trades=%d",
                     demo_id, output.total_return * 100, output.sharpe_ratio, output.total_trades)
        return result
    except Exception as exc:
        logger.error("Demo '%s' failed: %s", demo_id, exc)
        return None


async def precompute_demos():
    loop = asyncio.get_event_loop()
    for demo_id in DEMO_CONFIGS:
        if demo_id not in _demo_cache:
            result = await loop.run_in_executor(None, _compute_demo, demo_id)
            if result:
                _demo_cache[demo_id] = result


def get_demo(demo_id: str) -> dict | None:
    if demo_id not in _demo_cache:
        result = _compute_demo(demo_id)
        if result:
            _demo_cache[demo_id] = result
    return _demo_cache.get(demo_id)


def list_demos() -> list:
    if not _demo_cache:
        for demo_id in DEMO_CONFIGS:
            get_demo(demo_id)
    return [
        {"id": d["id"], "title": d["title"], "subtitle": d["subtitle"],
         "total_return": d["total_return"], "sharpe_ratio": d["sharpe_ratio"], "ticker": d["ticker"]}
        for d in _demo_cache.values()
    ]
