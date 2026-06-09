"""
Parameter optimization endpoints.

POST /api/v1/optimize/run           — run grid search optimization
POST /api/v1/optimize/preview-count — preview combination count
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.response import success_response, error_http
from app.models.user import User
from app.api.deps import get_current_user
from app.services.optimization_engine import (
    OptimizationInput,
    run_optimization,
    expand_param_ranges,
    filter_valid_combos,
)

router = APIRouter()

PLAN_LIMITS = {"free": 0, "pro": 100, "quant": 1000}


class ParamRangeSpec(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    values: Optional[list] = None


class OptimizeRequest(BaseModel):
    ticker: Optional[str] = None
    data_source: str = "yahoo"
    strategy_type: str
    param_ranges: dict[str, ParamRangeSpec]
    optimize_metric: str = "sharpe_ratio"
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 10000.0
    commission: float = 0.001


class PreviewRequest(BaseModel):
    strategy_type: str
    param_ranges: dict[str, ParamRangeSpec]


@router.post("/preview-count")
async def preview_count(
    body: PreviewRequest,
    current_user: User = Depends(get_current_user),
):
    """Preview how many combinations a grid search would produce."""
    plan = current_user.plan.value if hasattr(current_user.plan, "value") else "free"
    max_allowed = PLAN_LIMITS.get(plan, 0)

    all_combos = expand_param_ranges(
        {k: v.model_dump(exclude_none=True) for k, v in body.param_ranges.items()}
    )
    valid = filter_valid_combos(body.strategy_type, all_combos)

    return success_response(data={
        "total_combinations": len(valid),
        "max_allowed": max_allowed,
        "exceeds_limit": len(valid) > max_allowed,
        "estimated_seconds": round(len(valid) * 0.05, 1),
        "plan": plan,
    })


@router.post("/run")
async def run_optimize(
    body: OptimizeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a grid-search parameter optimization."""
    plan = current_user.plan.value if hasattr(current_user.plan, "value") else "free"
    max_combos = PLAN_LIMITS.get(plan, 0)

    if max_combos == 0:
        raise error_http(
            "plan_limit.exceeded",
            "Parameter optimization requires Pro or Quant plan. "
            "Upgrade to unlock grid search and walk-forward analysis.",
            status_code=403,
        )

    # Fetch data
    from app.services.data_service import get_yahoo_data
    df = await get_yahoo_data(body.ticker or "SPY", body.start_date, body.end_date)

    # Run optimization
    opt_input = OptimizationInput(
        df=df,
        strategy_type=body.strategy_type,
        param_ranges={k: v.model_dump(exclude_none=True) for k, v in body.param_ranges.items()},
        initial_capital=body.initial_capital,
        commission=body.commission,
        optimize_metric=body.optimize_metric,
        max_combinations=max_combos,
    )
    result = run_optimization(opt_input)

    return success_response(data={
        "best_params": result.best_params,
        "best_metrics": result.best_metrics,
        "all_results": result.all_results,
        "total_combinations": result.total_combinations,
        "heatmap_data": result.heatmap_data,
        "computation_time": result.computation_time,
    })
