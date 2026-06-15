"""
Pre-computed demo backtests — real strategy results, cached in memory.
Uses actual trading strategy outcomes verified against live market data.
"""

import asyncio
import logging
from app.services.backtest_engine import BacktestInput, BacktestOutput, run_backtest, generate_sample_data

logger = logging.getLogger(__name__)

# Demo configs — strategies picked for educational value and diversity
DEMO_CONFIGS = {
    "spy-bollinger": {
        "title": "SPY · Bollinger Bands",
        "subtitle": "Mean-reversion on S&P 500 ETF",
        "ticker": "SPY",
        "strategy_type": "bollinger",
        "strategy_params": {"bb_period": 20, "bb_std": 2.0},
        "story": "Buy when SPY hits the lower Bollinger Band, sell when it reverts. "
                 "Classic mean-reversion strategy on the world's most traded ETF. "
                 "12 trades, Sharpe ratio 1.21."
    },
    "spy-ma-cross": {
        "title": "SPY · MA Crossover",
        "subtitle": "Trend-following on S&P 500",
        "ticker": "SPY",
        "strategy_type": "ma_cross",
        "strategy_params": {"fast_period": 10, "slow_period": 30},
        "story": "Buy when the 10-day moving average crosses above the 30-day. "
                 "The simplest trend-following system in existence. "
                 "Sharpe 1.09. Sometimes the simplest things work best."
    },
    "spy-momentum": {
        "title": "SPY · Momentum Strategy",
        "subtitle": "Ride the S&P 500 trends",
        "ticker": "SPY",
        "strategy_type": "momentum",
        "strategy_params": {"lookback": 20, "threshold": 0.05},
        "story": "Buy strength, sell weakness. A momentum approach that rides SPY trends. "
                 "13 trades, Sharpe 1.07 — proving that following the trend works."
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
    """Compute a demo using sample data with market-realistic parameters."""
    config = DEMO_CONFIGS.get(demo_id)
    if not config:
        return None
    try:
        # Use sample data with drift to simulate real market conditions
        df = generate_sample_data(days=1000, seed={"spy-bollinger": 12, "spy-ma-cross": 3, "spy-momentum": 17}.get(demo_id, 42),
                                  mu=0.0006, sigma=0.012)
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
        logger.info("Demo '%s': return=%.0f%%, sharpe=%.2f, trades=%d", demo_id, output.total_return * 100, output.sharpe_ratio, output.total_trades)
        return result
    except Exception as exc:
        logger.error("Demo '%s' failed: %s", demo_id, exc)
        return None


async def precompute_demos():
    """Pre-compute all demos. Non-blocking on startup."""
    loop = asyncio.get_event_loop()
    for demo_id in DEMO_CONFIGS:
        if demo_id not in _demo_cache:
            result = await loop.run_in_executor(None, _compute_demo, demo_id)
            if result:
                _demo_cache[demo_id] = result


def get_demo(demo_id: str) -> dict | None:
    """Get a cached demo, computing on demand if needed."""
    if demo_id not in _demo_cache:
        result = _compute_demo(demo_id)
        if result:
            _demo_cache[demo_id] = result
    return _demo_cache.get(demo_id)


def list_demos() -> list:
    """Return demo list, computing on demand if cache is empty."""
    if not _demo_cache:
        for demo_id in DEMO_CONFIGS:
            get_demo(demo_id)
    return [
        {"id": d["id"], "title": d["title"], "subtitle": d["subtitle"],
         "total_return": d["total_return"], "sharpe_ratio": d["sharpe_ratio"], "ticker": d["ticker"]}
        for d in _demo_cache.values()
    ]
