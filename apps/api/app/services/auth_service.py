
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.security import (
    hash_password,
    verify_password,
    verify_password_and_update,
)


class AuthService:
    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        stmt = select(User).where(User.email == email.strip().lower())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def register(db: AsyncSession, payload: RegisterRequest) -> User:
        clean_email = str(payload.email).strip().lower()
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
        try:
            await db.commit()
        except IntegrityError as error:
            await db.rollback()
            raise ValueError("An account already exists for this email address.") from error
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, payload: LoginRequest) -> User | None:
        clean_email = str(payload.email).strip().lower()
        user = await AuthService.get_by_email(db, clean_email)
        if not user or not user.is_active:
            return None

        verified, replacement_hash = verify_password_and_update(payload.password, user.password_hash)
        if not verified:
            return None
        if replacement_hash:
            user.password_hash = replacement_hash
            await db.commit()
            await db.refresh(user)
        return user

    @staticmethod
    async def change_password(
        db: AsyncSession,
        user: User,
        current_password: str,
        new_password: str,
    ) -> User:
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect.")
        if verify_password(new_password, user.password_hash):
            raise ValueError("Choose a new password that is different from your current password.")

        user.password_hash = hash_password(new_password)
        await db.commit()
        await db.refresh(user)
        return user


auth_service = AuthService()
