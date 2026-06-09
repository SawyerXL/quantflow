"""
Pre-computed demo backtests — cached in memory, no DB queries, no user quotas.
"""

import asyncio
import logging
from app.services.backtest_engine import BacktestInput, BacktestOutput, run_backtest, generate_sample_data

logger = logging.getLogger(__name__)

DEMO_CONFIGS = {
    "qqq-donchian": {
        "title": "QQQ · Turtle Trading (Donchian)",
        "subtitle": "Breakout strategy on Nasdaq 100 ETF",
        "ticker": "QQQ",
        "strategy_type": "donchian",
        "strategy_params": {"entry_period": 20, "exit_period": 10},
        "story": "The Turtle Traders made millions with this breakout system back in the 1980s. "
                 "See how it performs on QQQ — the Nasdaq 100 ETF."
    },
    "spy-momentum": {
        "title": "SPY · Momentum Strategy",
        "subtitle": "Ride the trend on S&P 500",
        "ticker": "SPY",
        "strategy_type": "momentum",
        "strategy_params": {"lookback": 20, "threshold": 0.05},
        "story": "Buy strong, sell weak. A simple momentum approach that rides the S&P 500 trends. "
                 "High win rate, disciplined exits."
    },
    "btc-dualma": {
        "title": "BTC · Triple Moving Average",
        "subtitle": "Trend-following on Bitcoin",
        "ticker": "BTC-USD",
        "strategy_type": "dual_ma",
        "strategy_params": {"short_period": 5, "mid_period": 20, "long_period": 60},
        "story": "Bitcoin's wild volatility meets trend-following. "
                 "See how a triple-MA system navigates the chaos of crypto markets."
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
    """Synchronous computation using sample data (fast, no network dependency)."""
    config = DEMO_CONFIGS.get(demo_id)
    if not config:
        return None
    try:
        df = generate_sample_data(days=1000, seed={"qqq-donchian": 1, "spy-momentum": 2, "btc-dualma": 3}.get(demo_id, 42))
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
        logger.info("Demo '%s' precomputed: return=%.2f%%, trades=%d", demo_id, output.total_return, output.total_trades)
        return result
    except Exception as exc:
        logger.error("Demo '%s' compute failed: %s", demo_id, exc)
        return None


async def precompute_demos():
    """Pre-compute all demos in a thread pool. Non-blocking on startup."""
    loop = asyncio.get_event_loop()
    for demo_id in DEMO_CONFIGS:
        if demo_id not in _demo_cache:
            result = await loop.run_in_executor(None, _compute_demo, demo_id)
            if result:
                _demo_cache[demo_id] = result


def get_demo(demo_id: str) -> dict | None:
    """Get a cached demo. If not cached, compute synchronously."""
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
