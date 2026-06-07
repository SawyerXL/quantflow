"""
Auth endpoints — register, login, refresh, me.

POST /api/v1/auth/register  — create account, return tokens
POST /api/v1/auth/login     — authenticate, return tokens
POST /api/v1/auth/refresh   — exchange refresh token for new access token
GET  /api/v1/auth/me        — current user profile
"""

from fastapi import APIRouter, Depends
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


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Return the currently authenticated user's profile."""
    return success_response(
        data=UserResponse.model_validate(current_user).model_dump(),
    )
