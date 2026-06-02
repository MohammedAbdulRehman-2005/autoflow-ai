"""
AutoFlow AI X — Auth service layer.
All business logic for authentication lives here.
The router is kept thin — it only handles HTTP concerns.
"""

import uuid
from datetime import timedelta

import redis.asyncio as aioredis
from jose import JWTError
from sqlalchemy.orm import Session

from backend.auth.schemas import SignupRequest, LoginRequest, TokenResponse, AuthResponse, UserProfile
from backend.auth.utils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.core.config import get_settings
from backend.database.models import User

settings = get_settings()

# Redis key prefix for refresh tokens
# Format: "refresh:{jti}" → user_id (string)
_REFRESH_PREFIX = "refresh:"


def _make_redis_key(jti: str) -> str:
    return f"{_REFRESH_PREFIX}{jti}"


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

async def _store_refresh_token(redis: aioredis.Redis, jti: str, user_id: uuid.UUID) -> None:
    """Persist the refresh token jti → user_id mapping in Redis with TTL."""
    ttl_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
    await redis.setex(_make_redis_key(jti), ttl_seconds, str(user_id))


async def _revoke_refresh_token(redis: aioredis.Redis, jti: str) -> None:
    """Delete a refresh token from Redis, effectively invalidating it."""
    await redis.delete(_make_redis_key(jti))


async def _validate_refresh_token_in_redis(redis: aioredis.Redis, jti: str) -> str | None:
    """
    Return the stored user_id string if the jti exists in Redis,
    or None if the token has been revoked or never existed.
    """
    return await redis.get(_make_redis_key(jti))


def _build_token_response(user_id: uuid.UUID) -> tuple[str, str, TokenResponse]:
    """Create a fresh access + refresh token pair and return the response schema."""
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return access_token, refresh_token, token_response


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

async def signup_user(
    payload: SignupRequest,
    db: Session,
    redis: aioredis.Redis,
) -> AuthResponse:
    """
    Register a new user.
    Raises ValueError on duplicate email.
    """
    # 1. Check for existing user
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise ValueError("An account with this email already exists.")

    # 2. Create user
    new_user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 3. Generate tokens
    _, refresh_token, token_response = _build_token_response(new_user.id)

    # 4. Store refresh token jti in Redis
    payload_decoded = decode_token(refresh_token)
    await _store_refresh_token(redis, payload_decoded["jti"], new_user.id)

    return AuthResponse(
        user=UserProfile.model_validate(new_user),
        tokens=token_response,
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def login_user(
    payload: LoginRequest,
    db: Session,
    redis: aioredis.Redis,
) -> AuthResponse:
    """
    Authenticate an existing user.
    Raises ValueError on invalid credentials.
    """
    # 1. Lookup user — use a generic error message to prevent user enumeration
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise ValueError("Invalid email or password.")

    # 2. Check account is active
    if not user.is_active:
        raise ValueError("Your account has been deactivated. Please contact support.")

    # 3. Generate tokens
    _, refresh_token, token_response = _build_token_response(user.id)

    # 4. Store refresh token
    payload_decoded = decode_token(refresh_token)
    await _store_refresh_token(redis, payload_decoded["jti"], user.id)

    return AuthResponse(
        user=UserProfile.model_validate(user),
        tokens=token_response,
    )


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

async def refresh_access_token(
    refresh_token: str,
    db: Session,
    redis: aioredis.Redis,
) -> TokenResponse:
    """
    Issue a new access token using a valid refresh token.
    Implements token rotation: the old refresh token is revoked and a new one issued.
    Raises ValueError if the token is invalid, expired, or revoked.
    """
    # 1. Decode and verify JWT signature & expiry
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise ValueError("Invalid or expired refresh token.")

    # 2. Ensure this is actually a refresh token
    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type.")

    jti: str = payload.get("jti", "")
    user_id_str: str = payload.get("sub", "")

    # 3. Validate against Redis (checks it hasn't been revoked)
    stored_user_id = await _validate_refresh_token_in_redis(redis, jti)
    if stored_user_id is None:
        raise ValueError("Refresh token has been revoked.")

    if stored_user_id != user_id_str:
        raise ValueError("Token mismatch.")

    # 4. Confirm user still exists and is active
    user = db.query(User).filter(User.id == uuid.UUID(user_id_str)).first()
    if not user or not user.is_active:
        raise ValueError("User not found or deactivated.")

    # 5. Token rotation: revoke old jti, issue new pair
    await _revoke_refresh_token(redis, jti)
    _, new_refresh_token, token_response = _build_token_response(user.id)
    new_payload = decode_token(new_refresh_token)
    await _store_refresh_token(redis, new_payload["jti"], user.id)

    return token_response


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

async def logout_user(
    refresh_token: str,
    redis: aioredis.Redis,
) -> None:
    """
    Invalidate a refresh token.
    Silently succeeds if the token is already revoked (idempotent).
    """
    try:
        payload = decode_token(refresh_token)
        jti = payload.get("jti", "")
        if jti:
            await _revoke_refresh_token(redis, jti)
    except JWTError:
        # If the token is already expired/invalid we still consider logout a success
        pass
