"""
Auth utilities: password hashing, JWT access + refresh tokens.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from app.core.config import get_settings

settings = get_settings()

ACCESS_TOKEN_EXPIRE = timedelta(hours=24)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    to_encode = {
        "sub": subject,
        "exp": now + expires_delta,
        "iat": now,
        "type": token_type,
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _create_token(user_id, ACCESS_TOKEN_EXPIRE, "access")


def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, REFRESH_TOKEN_EXPIRE, "refresh")


def decode_token(token: str, expected_type: str | None = None) -> str | None:
    """Decode and validate a JWT. Returns the user_id (sub) or None."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None

    if expected_type and payload.get("type") != expected_type:
        return None

    return payload.get("sub")
