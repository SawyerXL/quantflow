"""
Parameter optimization engine — grid search over strategy parameters.

Uses vectorized backtesting to evaluate many parameter combinations quickly.
"""

import itertools
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import HTTPException

from app.services.backtest_engine import (
    BacktestInput,
    BacktestOutput,
    STRATEGY_FUNCTIONS,
    _simulate_trades,
    _max_drawdown_duration,
    TRADING_DAYS,
)

logger = logging.getLogger(__name__)

METRIC_LABELS = {
    "total_return": "Total Return",
    "sharpe_ratio": "Sharpe Ratio",
    "max_drawdown": "Max Drawdown",
    "win_rate": "Win Rate",
    "profit_factor": "Profit Factor",
}


@dataclass
class OptimizationInput:
    df: pd.DataFrame
    strategy_type: str
    param_ranges: dict
    initial_capital: float = 10000.0
    commission: float = 0.001
    optimize_metric: str = "sharpe_ratio"
    max_combinations: int = 100


@dataclass
class OptimizationResult:
    best_params: dict
    best_metrics: dict
    all_results: list = field(default_factory=list)
    total_combinations: int = 0
    optimize_metric: str = "sharpe_ratio"
    heatmap_data: Optional[dict] = None
    computation_time: float = 0.0


# ============================================================
# Parameter range expansion
# ============================================================

def expand_param_ranges(param_ranges: dict) -> list[dict]:
    """Expand {param: {min, max, step}} or {param: {values: [...]}} into list of dicts."""
    param_lists = {}
    for name, spec in param_ranges.items():
        if "values" in spec:
            param_lists[name] = spec["values"]
        else:
            if "min" not in spec or "max" not in spec:
                raise HTTPException(400, f"Parameter '{name}' missing min/max")
            min_v = spec["min"]
            max_v = spec["max"]
            step = spec.get("step", 1)
            values = list(np.arange(min_v, max_v + step * 0.1, step))
            if isinstance(min_v, int) and isinstance(step, int):
                values = [int(v) for v in values]
            param_lists[name] = values

    keys = list(param_lists.keys())
    return [dict(zip(keys, combo)) for combo in itertools.product(*param_lists.values())]


def filter_valid_combos(strategy_type: str, combos: list[dict]) -> list[dict]:
    """Remove logically impossible parameter combinations."""
    valid = []
    for params in combos:
        skip = False
        if strategy_type in ("ma_cross", "ema_cross", "macd"):
            if params.get("fast_period", 0) >= params.get("slow_period", 999):
                skip = True
        elif strategy_type == "dual_ma":
            s = params.get("short_period", 0); m = params.get("mid_period", 100); l = params.get("long_period", 200)
            if not (s < m < l):
                skip = True
        elif strategy_type in ("rsi", "kdj", "cci"):
            if params.get("oversold", 0) >= params.get("overbought", 100):
                skip = True
        if not skip:
            valid.append(params)
    return valid


# ============================================================
# Main optimization function
# ============================================================

def run_optimization(input: OptimizationInput) -> OptimizationResult:
    """Run grid search over all parameter combinations."""
    t0 = time.time()

    # 1. Expand & filter combos
    all_combos = expand_param_ranges(input.param_ranges)
    if len(all_combos) > input.max_combinations:
        raise HTTPException(400, {
            "code": "TOO_MANY_COMBINATIONS",
            "message": f"Generates {len(all_combos)} combos (limit: {input.max_combinations})",
            "suggestion": "Reduce parameter ranges or increase step size",
        })

    valid = filter_valid_combos(input.strategy_type, all_combos)
    if not valid:
        raise HTTPException(400, "No valid parameter combinations found")

    # 2. Prepare data
    df = input.df.copy()
    close = df["close"]

    # 3. Run each combination
    results = []
    for params in valid:
        try:
            # Generate signals
            strategy_fn = STRATEGY_FUNCTIONS[input.strategy_type]
            entries, exits = strategy_fn(close, params)

            if entries.sum() == 0:
                continue

            # Simulate
            equity, trades = _simulate_trades(
                close, entries, exits, input.initial_capital, input.commission
            )

            # Metrics
            returns = equity.pct_change().dropna()
            total_return = float(equity.iloc[-1] / input.initial_capital - 1)
            annual_return = float((1 + total_return) ** (TRADING_DAYS / len(returns)) - 1) if len(returns) > 1 else 0
            sharpe = float((returns.mean() / returns.std()) * np.sqrt(TRADING_DAYS)) if len(returns) > 1 and returns.std() > 0 else 0
            dd = (equity - equity.cummax()) / equity.cummax()
            max_dd = float(dd.min())

            if np.isnan(sharpe) or np.isinf(sharpe):
                sharpe = 0.0

            wins = [t for t in trades if t["pnl"] > 0]
            losses = [t for t in trades if t["pnl"] < 0]
            win_rate = len(wins) / len(trades) if trades else 0
            total_profit = sum(t["pnl"] for t in wins) if wins else 0
            total_loss = abs(sum(t["pnl"] for t in losses)) if losses else 1
            profit_factor = total_profit / total_loss if total_loss else 0

            results.append({
                "params": params,
                "total_return": round(total_return * 100, 2),
                "annual_return": round(annual_return * 100, 2),
                "sharpe_ratio": round(sharpe, 3),
                "max_drawdown": round(max_dd * 100, 2),
                "win_rate": round(win_rate * 100, 2),
                "total_trades": len(trades),
                "profit_factor": round(profit_factor, 2),
            })
        except Exception as exc:
            logger.debug("Combo %s failed: %s", params, exc)

    if not results:
        raise HTTPException(400, "No combinations produced valid results")

    # 4. Sort by target metric
    metric = input.optimize_metric
    reverse = metric != "max_drawdown"  # max_dd is negative, higher is better
    results.sort(key=lambda r: r.get(metric, 0), reverse=reverse)

    # 5. Heatmap for 2 numeric params
    heatmap = _build_heatmap(results, input.param_ranges, metric)

    return OptimizationResult(
        best_params=results[0]["params"],
        best_metrics={k: v for k, v in results[0].items() if k != "params"},
        all_results=results,
        total_combinations=len(results),
        optimize_metric=metric,
        heatmap_data=heatmap,
        computation_time=round(time.time() - t0, 2),
    )


def _build_heatmap(results, param_ranges, metric) -> Optional[dict]:
    """Build 2D heatmap data when exactly 2 numeric parameters exist."""
    numeric = [k for k, v in param_ranges.items() if "values" not in v]
    if len(numeric) != 2:
        return None

    xp, yp = numeric
    xv = sorted(set(r["params"][xp] for r in results))
    yv = sorted(set(r["params"][yp] for r in results))
    matrix = [
        [next((r[metric] for r in results if r["params"][xp] == x and r["params"][yp] == y), None) for x in xv]
        for y in yv
    ]
    return {"x_param": xp, "y_param": yp, "x_values": xv, "y_values": yv, "matrix": matrix, "metric": metric}
