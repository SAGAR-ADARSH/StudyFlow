from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, PasswordChangeRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import auth_service
from app.services.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.password_hash),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        user = await auth_service.register(db, payload)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await auth_service.authenticate(db, payload)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_response(user)


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        user = await auth_service.change_password(
            db,
            current_user,
            payload.current_password,
            payload.new_password,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    # Password-bound token signatures revoke the old session family; this fresh token
    # keeps the device performing the change signed in.
    return _token_response(user)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return UserResponse.model_validate(current_user)
