from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserUpdateRequest


class UserService:
    @staticmethod
    async def update_profile(db: AsyncSession, user: User, payload: UserUpdateRequest) -> User:
        if payload.display_name is not None:
            user.display_name = payload.display_name
        if payload.college_name is not None:
            user.college_name = payload.college_name or None
        if payload.course_name is not None:
            user.course_name = payload.course_name or None

        await db.commit()
        await db.refresh(user)
        return user


user_service = UserService()
