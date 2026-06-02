"""
AutoFlow AI X — FastAPI dependency injection for authentication.
Import `get_current_user` and use it as a Depends() on any protected route.

Usage:
    @router.get("/me")
    def me(current_user: User = Depends(get_current_user)):
        ...
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from backend.auth.utils import decode_token
from backend.database.models import User
from backend.database.session import get_db

# Extracts "Bearer <token>" from the Authorization header
_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that validates the JWT access token from the Authorization header
    and returns the corresponding User ORM object.

    Raises HTTP 401 on:
      - Missing Authorization header
      - Invalid or expired token
      - User not found in the database
      - User account deactivated (soft-deleted or is_active=False)
    """
    _unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Ensure the Authorization header is present
    if credentials is None:
        raise _unauthorized

    token = credentials.credentials

    # 2. Decode and validate the JWT
    try:
        payload = decode_token(token)
    except JWTError:
        raise _unauthorized

    # 3. Confirm this is an access token (not a refresh token)
    if payload.get("type") != "access":
        raise _unauthorized

    # 4. Extract and validate the user ID
    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise _unauthorized

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise _unauthorized

    # 5. Load the user from the database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise _unauthorized

    # 6. Reject soft-deleted or deactivated accounts
    if not user.is_active or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is deactivated.",
        )

    return user
