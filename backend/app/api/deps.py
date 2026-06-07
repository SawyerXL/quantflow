"""
FastAPI dependencies: auth extraction, rate limiting, user lookup.
"""

import time
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.enums import enum_value
from app.models.user import User

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


# ── Current user (JWT required) ──────────────────────────────────────────────


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "auth.token_invalid", "message": "Authorization header required"},
        )
    user_id = decode_token(credentials.credentials, expected_type="access")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "auth.token_invalid", "message": "Invalid or expired access token"},
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "auth.token_invalid", "message": "User not found or inactive"},
        )
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising 401."""
    if credentials is None:
        return None
    user_id = decode_token(credentials.credentials, expected_type="access")
    if user_id is None:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ── Rate limiting ─────────────────────────────────────────────────────────────


async def check_rate_limit(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> None:
    """Check rate limit for the current user. Raises 429 if exceeded."""
    if not settings.RATE_LIMIT_ENABLED:
        return

    max_requests = settings.RATE_LIMIT_PRO_USER if enum_value(current_user.plan) != "free" else settings.RATE_LIMIT_FREE_USER
    if max_requests == 0:
        return  # Unlimited

    now = int(time.time())
    window_start = now - settings.RATE_LIMIT_WINDOW_SECONDS
    user_key = f"quantflow:ratelimit:{current_user.id}"

    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        # Remove old entries, add current, count
        pipe = r.pipeline()
        pipe.zremrangebyscore(user_key, 0, window_start)
        pipe.zadd(user_key, {str(now): now})
        pipe.zcard(user_key)
        pipe.expire(user_key, settings.RATE_LIMIT_WINDOW_SECONDS + 60)
        _, _, count, _ = await pipe.execute()

        if count > max_requests:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "rate_limit.exceeded",
                    "message": f"Rate limit exceeded: {max_requests} requests per hour. "
                               f"Upgrade to Pro for unlimited access.",
                },
            )
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        # If Redis is down, skip rate limiting (don't block users)
        pass


# ── Plan permission checks ────────────────────────────────────────────────────


PLAN_LIMITS = {
    "free": {
        "backtests_per_day": 5,
        "api_access": False,
        "export_pdf": False,
        "custom_strategies": False,
    },
    "pro": {
        "backtests_per_day": -1,
        "api_access": False,
        "export_pdf": True,
        "custom_strategies": True,
    },
    "quant": {
        "backtests_per_day": -1,
        "api_access": True,
        "export_pdf": True,
        "custom_strategies": True,
    },
}


def check_plan_limit(user: User, action: str) -> None:
    """
    Check if the user's plan allows the given action.

    Actions: run_backtest, api_access, export_pdf, custom_strategy.
    Raises HTTPException 403 with an upgrade_url on limit exceeded.
    """
    plan = enum_value(user.plan)
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    if action == "run_backtest":
        max_allowed = limits["backtests_per_day"]
        if max_allowed != -1 and user.backtest_count_today >= max_allowed:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "plan_limit.exceeded",
                    "message": (
                        f"Daily backtest limit reached ({max_allowed}/day on "
                        f"{plan.capitalize()}). Upgrade for unlimited backtests."
                    ),
                    "upgrade_url": "/billing",
                },
            )

    elif action == "api_access":
        if not limits["api_access"]:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "plan_limit.exceeded",
                    "message": f"API access requires the Quant plan.",
                    "upgrade_url": "/billing",
                },
            )

    elif action in ("export_pdf", "custom_strategy"):
        if not limits.get(action.replace("custom_strategy", "custom_strategies"), limits.get("export_pdf")):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "plan_limit.exceeded",
                    "message": f"{action.replace('_', ' ').title()} requires Pro or Quant plan.",
                    "upgrade_url": "/billing",
                },
            )

    else:
        raise ValueError(f"Unknown plan action: {action}")
