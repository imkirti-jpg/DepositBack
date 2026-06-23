from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.schemas.profile import ProfileUpdate


class ProfileService:

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        profile: User,
        payload: ProfileUpdate
    ):

        update_data = payload.model_dump(
            exclude_unset=True
        )

        for field, value in update_data.items():
            setattr(profile, field, value)

        await db.commit()
        await db.refresh(profile)

        return profile