"""
Dashboard stats endpoint.

GET /api/v1/dashboard/stats — real statistics for the current user.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response
from app.models.user import User
from app.models.backtest import BacktestResult
from app.models.enums import BacktestStatus
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's dashboard statistics."""
    # Count completed backtests
    total = await db.scalar(
        select(func.count())
        .select_from(BacktestResult)
        .where(
            BacktestResult.user_id == current_user.id,
            BacktestResult.status == BacktestStatus.completed,
        )
    )

    if not total:
        return success_response(data={
            "has_data": False,
            "total_backtests": 0,
            "backtests_today": current_user.backtest_count_today,
            "stats": None,
        })

    # Aggregated stats
    avg_sharpe = await db.scalar(
        select(func.avg(BacktestResult.sharpe_ratio))
        .where(
            BacktestResult.user_id == current_user.id,
            BacktestResult.status == BacktestStatus.completed,
            BacktestResult.sharpe_ratio.isnot(None),
        )
    )

    avg_return = await db.scalar(
        select(func.avg(BacktestResult.total_return))
        .where(
            BacktestResult.user_id == current_user.id,
            BacktestResult.status == BacktestStatus.completed,
            BacktestResult.total_return.isnot(None),
        )
    )

    # Best backtest by return
    best_result = await db.execute(
        select(BacktestResult)
        .where(
            BacktestResult.user_id == current_user.id,
            BacktestResult.status == BacktestStatus.completed,
            BacktestResult.total_return.isnot(None),
        )
        .order_by(BacktestResult.total_return.desc())
        .limit(1)
    )
    best = best_result.scalar_one_or_none()

    # Most recent backtests (last 7)
    recent = await db.execute(
        select(BacktestResult)
        .where(
            BacktestResult.user_id == current_user.id,
            BacktestResult.status == BacktestStatus.completed,
        )
        .order_by(BacktestResult.created_at.desc())
        .limit(7)
    )
    recent_list = recent.scalars().all()

    return success_response(data={
        "has_data": True,
        "total_backtests": total,
        "backtests_today": current_user.backtest_count_today,
        "stats": {
            "avg_sharpe": round(float(avg_sharpe or 0), 2),
            "avg_return": round(float(avg_return or 0), 2),
            "best_return": round(float(best.total_return), 4) if best else None,
            "best_name": best.name if best else None,
            "best_ticker": best.ticker if best else None,
            "recent": [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "ticker": r.ticker,
                    "total_return": r.total_return,
                    "sharpe_ratio": r.sharpe_ratio,
                    "win_rate": r.win_rate,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in recent_list
            ],
        },
    })
