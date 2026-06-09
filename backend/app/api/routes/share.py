"""
Share endpoints — create, revoke, and view shared backtests.

POST   /api/v1/backtest/{id}/share  — create share link
DELETE /api/v1/backtest/{id}/share  — revoke share link
GET    /api/v1/share/{slug}         — view shared backtest (public, no auth)
"""

import secrets
import string
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response, error_http
from app.models.user import User
from app.models.backtest import BacktestResult
from app.models.enums import BacktestStatus
from app.api.deps import get_current_user

router = APIRouter()
FRONTEND_URL = "https://quantflow.pages.dev"
_ALPHABET = string.ascii_letters + string.digits


async def _generate_slug(db: AsyncSession) -> str:
    """Generate a unique 12-character share slug."""
    for _ in range(5):
        slug = "".join(secrets.choice(_ALPHABET) for _ in range(12))
        result = await db.execute(
            select(BacktestResult).where(BacktestResult.share_slug == slug)
        )
        if not result.scalar_one_or_none():
            return slug
    raise RuntimeError("Failed to generate unique share slug")


@router.post("/{backtest_id}/share")
async def create_share(
    backtest_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or return an existing share link for a backtest."""
    result = await db.execute(
        select(BacktestResult).where(BacktestResult.id == backtest_id)
    )
    bt = result.scalar_one_or_none()

    if not bt:
        raise error_http("resource.not_found", "Backtest not found", status_code=404)
    if bt.user_id != current_user.id:
        raise error_http("auth.insufficient_permissions", "Not your backtest", status_code=403)
    if bt.status != BacktestStatus.completed:
        raise error_http("validation.error", "Can only share completed backtests", status_code=400)

    # Return existing link if already shared
    if bt.is_shared and bt.share_slug:
        return success_response(data={
            "share_url": f"{FRONTEND_URL}/s/{bt.share_slug}",
            "slug": bt.share_slug,
            "view_count": bt.share_view_count,
        })

    slug = await _generate_slug(db)
    bt.share_slug = slug
    bt.is_shared = True
    bt.share_created_at = datetime.now(timezone.utc)
    await db.commit()

    return success_response(data={
        "share_url": f"{FRONTEND_URL}/s/{slug}",
        "slug": slug,
        "view_count": 0,
    })


@router.delete("/{backtest_id}/share")
async def revoke_share(
    backtest_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a share link."""
    result = await db.execute(
        select(BacktestResult).where(BacktestResult.id == backtest_id)
    )
    bt = result.scalar_one_or_none()
    if not bt:
        raise error_http("resource.not_found", "Backtest not found", status_code=404)
    if bt.user_id != current_user.id:
        raise error_http("auth.insufficient_permissions", "Not your backtest", status_code=403)

    bt.is_shared = False
    bt.share_slug = None
    await db.commit()

    return success_response(data={"message": "Share link revoked"})


@router.get("/{slug}")
async def view_shared(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """View a shared backtest. No authentication required."""
    result = await db.execute(
        select(BacktestResult).where(
            BacktestResult.share_slug == slug,
            BacktestResult.is_shared == True,
        )
    )
    bt = result.scalar_one_or_none()

    if not bt:
        raise error_http("resource.not_found", "This shared backtest no longer exists", status_code=404)

    # Increment view count (fire-and-forget)
    try:
        bt.share_view_count += 1
        await db.commit()
    except Exception:
        pass

    return success_response(data={
        "name": bt.name,
        "ticker": bt.ticker,
        "strategy_type": bt.status.value if hasattr(bt.status, "value") else "completed",
        "start_date": bt.start_date.isoformat() if bt.start_date else None,
        "end_date": bt.end_date.isoformat() if bt.end_date else None,
        "initial_capital": bt.initial_capital,
        "total_return": bt.total_return,
        "annual_return": bt.annual_return,
        "sharpe_ratio": bt.sharpe_ratio,
        "max_drawdown": bt.max_drawdown,
        "win_rate": bt.win_rate,
        "total_trades": bt.total_trades,
        "profit_factor": bt.profit_factor,
        "result_data": bt.result_data,
        "view_count": bt.share_view_count,
        "created_at": bt.created_at.isoformat() if bt.created_at else None,
    })
