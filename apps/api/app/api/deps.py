from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import auth_service
from app.services.security import access_token_matches_password, decode_access_token

security_bearer = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if not credentials or not credentials.credentials:
        raise _unauthorized("Authentication required. Please provide a valid Bearer token.")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise _unauthorized() from None

    user = await auth_service.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise _unauthorized("User not found or inactive")
    if not access_token_matches_password(payload.get("pwd_sig"), user.password_hash):
        raise _unauthorized("This session is no longer valid. Please sign in again.")
    return user
