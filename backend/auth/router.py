"""
AutoFlow AI X — Authentication router.
All /auth/* endpoints live here. The router stays thin:
it handles HTTP concerns (status codes, headers) and delegates
all business logic to auth/service.py.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import service
from backend.auth.dependencies import get_current_user
from backend.auth.schemas import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserProfile,
)
from backend.core.redis import get_redis
from backend.database.models import User
from backend.database.session import get_db
import redis.asyncio as aioredis

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# POST /auth/signup
# ---------------------------------------------------------------------------

@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def signup(
    payload: SignupRequest,
    db: Session = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Create a new user account and return JWT access + refresh tokens.

    - Validates password strength (min 8 chars, 1 uppercase, 1 digit)
    - Rejects duplicate emails with 409 Conflict
    - Returns the created user profile alongside tokens
    """
    try:
        return await service.signup_user(payload, db, redis)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in with email and password",
)
async def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Authenticate with email and password.

    - Uses a generic error message to prevent user enumeration attacks
    - Returns JWT access token (15 min) and refresh token (7 days)
    """
    try:
        return await service.login_user(payload, db, redis)
    except ValueError as e:
        # Always return 401 for login failures — never 404 — to prevent enumeration
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh an access token using a refresh token",
)
async def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Exchange a valid refresh token for a new access token.

    Implements **token rotation**: the submitted refresh token is revoked
    and a fresh refresh token is returned alongside the new access token.
    This limits the damage if a refresh token is ever stolen.
    """
    try:
        return await service.refresh_access_token(payload.refresh_token, db, redis)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    summary="Get the current authenticated user's profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Returns the profile of the currently authenticated user.
    Requires a valid JWT access token in the Authorization header.
    """
    return UserProfile.model_validate(current_user)


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out and invalidate the refresh token",
)
async def logout(
    payload: RefreshRequest,
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Invalidate a refresh token, preventing it from being used to issue new tokens.
    This endpoint is idempotent — calling it on an already-revoked token still returns 200.

    Note: The access token remains valid until it expires (15 min).
    For immediate access token revocation, implement an access token denylist in Redis.
    """
    await service.logout_user(payload.refresh_token, redis)
    return MessageResponse(message="Successfully logged out.")
