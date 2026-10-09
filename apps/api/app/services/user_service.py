from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.user import UserUpdateRequest
from app.services.security import hash_password, verify_password


class UserService:
    @staticmethod
    async def update_profile(db: AsyncSession, user: User, payload: UserUpdateRequest) -> User:
        if payload.display_name is not None:
            user.display_name = payload.display_name.strip()
        if payload.college_name is not None:
            user.college_name = payload.college_name.strip() if payload.college_name else None
        if payload.course_name is not None:
            user.course_name = payload.course_name.strip() if payload.course_name else None

        if payload.new_password:
            if not payload.current_password or not verify_password(payload.current_password, user.password_hash):
                raise ValueError("Current password is incorrect.")
            user.password_hash = hash_password(payload.new_password)

        await db.commit()
        await db.refresh(user)
        return user


user_service = UserService()
