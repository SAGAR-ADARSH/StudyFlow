from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.security import hash_password, verify_password


class AuthService:
    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.strip().lower())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def register(db: AsyncSession, payload: RegisterRequest) -> User:
        clean_email = payload.email.strip().lower()
        existing = await AuthService.get_by_email(db, clean_email)
        if existing:
            raise ValueError("An account already exists for this email address.")

        user = User(
            email=clean_email,
            password_hash=hash_password(payload.password),
            display_name=payload.display_name.strip(),
            college_name=payload.college_name.strip() if payload.college_name else None,
            course_name=payload.course_name.strip() if payload.course_name else None,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, payload: LoginRequest) -> Optional[User]:
        clean_email = payload.email.strip().lower()
        user = await AuthService.get_by_email(db, clean_email)
        if not user:
            return None
        if not verify_password(payload.password, user.password_hash):
            return None
        return user


auth_service = AuthService()
