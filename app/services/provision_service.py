from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User , UserPreferences
from app.schemas import profile


class UserProvisioningService:
    @staticmethod
    async def provision_user(db: AsyncSession,user_id: UUID) -> User:

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            return user

        user = User(id=user_id)

        preference = UserPreferences(user_id=user_id)

        db.add(user)
        db.add(preference)

        await db.commit()

        await db.refresh(user)

        return user