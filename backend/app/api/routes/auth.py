"""
Auth endpoints — register, login, refresh, me.

POST /api/v1/auth/register  — create account, return tokens
POST /api/v1/auth/login     — authenticate, return tokens
POST /api/v1/auth/refresh   — exchange refresh token for new access token
GET  /api/v1/auth/me        — current user profile
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.response import success_response, error_http
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.schemas.user import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshRequest,
    AccessTokenResponse,
    UserResponse,
)
from app.api.deps import get_current_user
from app.services.billing_service import create_customer

router = APIRouter()


@router.post("/register", status_code=201)
async def register(
    body: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """Register a new account. Returns access and refresh tokens."""
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise error_http(
            "resource.conflict",
            "An account with this email already exists",
            status_code=409,
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()

    # Try to create a Stripe customer (best-effort, don't block registration)
    try:
        customer_id = await create_customer(body.email, body.full_name or "")
        if customer_id:
            user.stripe_customer_id = customer_id
    except Exception:
        pass  # Stripe not configured — register anyway

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    return success_response(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ).model_dump(),
        status_code=201,
    )


@router.post("/login")
async def login(
    body: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email and password. Returns access and refresh tokens."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        raise error_http(
            "auth.invalid_credentials",
            "Invalid email or password",
            status_code=401,
        )
    if not verify_password(body.password, user.hashed_password):
        raise error_http(
            "auth.invalid_credentials",
            "Invalid email or password",
            status_code=401,
        )
    if not user.is_active:
        raise error_http(
            "auth.insufficient_permissions",
            "Account is deactivated",
            status_code=403,
        )

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    return success_response(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ).model_dump(),
    )


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
):
    """Exchange a valid refresh token for a new access token."""
    user_id = decode_token(body.refresh_token, expected_type="refresh")
    if user_id is None:
        raise error_http(
            "auth.token_expired",
            "Refresh token is invalid or expired. Please log in again.",
            status_code=401,
        )

    access_token = create_access_token(user_id)
    return success_response(
        data=AccessTokenResponse(access_token=access_token).model_dump(),
    )


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for the currently authenticated user."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise error_http("auth.invalid_credentials", "Current password is incorrect", status_code=401)

    pwd = body.new_password
    if len(pwd) < 8:
        raise error_http("validation.error", "Password must be at least 8 characters", status_code=422)
    if not any(c.isalpha() for c in pwd):
        raise error_http("validation.error", "Password must contain at least one letter", status_code=422)
    if not any(c.isdigit() for c in pwd):
        raise error_http("validation.error", "Password must contain at least one digit", status_code=422)

    current_user.hashed_password = hash_password(pwd)
    await db.commit()
    return success_response(data={"message": "Password changed successfully"})


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
):
    """Logout — client should discard tokens. Server-side blacklist optional."""
    return success_response(data={"message": "Signed out successfully"})


# ── Forgot / Reset password ──────────────────────────────────────────────────

# In-memory token store (fallback when Redis/Upstash is unavailable)
_reset_tokens: dict[str, tuple[str, float]] = {}


async def _store_reset_token(token: str, user_id: str, ttl: int = 600):
    """Store a password reset token with TTL (seconds)."""
    import time
    try:
        from app.core.cache import redis_cache
        await redis_cache.set(f"pwd_reset:{token}", user_id, ttl=ttl)
    except Exception:
        _reset_tokens[token] = (user_id, time.time() + ttl)


async def _get_and_delete_reset_token(token: str) -> str | None:
    """Get user_id for a reset token, then delete it (one-time use)."""
    import time
    try:
        from app.core.cache import redis_cache
        val = await redis_cache.get(f"pwd_reset:{token}")
        if val:
            await redis_cache.delete(f"pwd_reset:{token}")
            return val
        return None
    except Exception:
        entry = _reset_tokens.pop(token, None)
        if entry and time.time() < entry[1]:
            return entry[0]
        return None


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset email. Always returns the same response
    regardless of whether the email exists (prevents enumeration)."""
    import secrets

    result = await db.execute(select(User).where(User.email == body.email.strip().lower()))
    user = result.scalar_one_or_none()

    if user:
        token = secrets.token_urlsafe(32)
        await _store_reset_token(token, str(user.id), ttl=600)

        reset_url = f"https://quantflow-two.vercel.app/reset-password?token={token}"
        try:
            from app.services.email_service import send_reset_email
            await send_reset_email(user.email, user.full_name or "", reset_url)
        except Exception:
            pass  # Email failure shouldn't reveal user existence

    return success_response(
        data={"message": "If this email exists, you will receive a reset link shortly."}
    )


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Complete password reset using the token from email."""
    # Validate password strength
    pwd = body.new_password
    if len(pwd) < 8:
        raise error_http("validation.error", "Password must be at least 8 characters", status_code=422)
    if not any(c.isalpha() for c in pwd):
        raise error_http("validation.error", "Password must contain at least one letter", status_code=422)
    if not any(c.isdigit() for c in pwd):
        raise error_http("validation.error", "Password must contain at least one digit", status_code=422)

    # Verify token
    user_id = await _get_and_delete_reset_token(body.token.strip())
    if not user_id:
        raise error_http("auth.token_expired", "Invalid or expired reset link. Please request a new one.", status_code=400)

    # Update password
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise error_http("resource.not_found", "User not found", status_code=404)

    user.hashed_password = hash_password(pwd)
    await db.commit()

    return success_response(data={"message": "Password reset successful. You can now sign in with your new password."})


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the currently authenticated user's profile, with plan limits and subscription info."""
    from app.services.billing_service import get_subscription_status

    sub_info = {"status": None, "current_period_end": None, "cancel_at_period_end": False}
    try:
        sub_info = await get_subscription_status(current_user)
    except Exception:
        pass

    plan_value = current_user.plan.value if hasattr(current_user.plan, "value") else str(current_user.plan)
    limits = {"free": 5, "pro": -1, "quant": -1}
    daily_limit = limits.get(plan_value, 5)

    data = {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "plan": plan_value,
        "plan_display_name": plan_value.capitalize(),
        "backtest_count_today": current_user.backtest_count_today,
        "backtest_limit_today": daily_limit,
        "subscription": sub_info if sub_info["status"] else None,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }
    return success_response(data=data)
