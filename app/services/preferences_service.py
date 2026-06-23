from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import UserPreferences
from app.schemas.preferences import PreferencesUpdate


class PreferenceService:
    @staticmethod
    async def get_preferences(db: AsyncSession, user_id):

        result = await db.execute(
            select(UserPreferences)
            .where(UserPreferences.user_id == user_id)
        )
        return result.scalar_one()

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        preference: UserPreferences,
        payload: PreferencesUpdate
    ):

        data = payload.model_dump()

        for field, value in data.items():
            setattr(preference, field, value)

        await db.commit()
        await db.refresh(preference)

        return preference