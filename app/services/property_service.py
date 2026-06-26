import uuid
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.models.property import Property
from app.schemas.property import (
    PropertyCreate,
    PropertyUpdate,
)
from app.services.analytics import track

logger = logging.getLogger(__name__)


class PropertyService:

    @staticmethod
    async def get_owned_property(
        db: AsyncSession,
        property_id: uuid.UUID,
        user: User,
    ) -> Property:

        result = await db.execute(
            select(Property).where(
                Property.id == property_id,
                Property.user_id == user.id,
            )
        )

        property_obj = result.scalar_one_or_none()

        if property_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found",
            )

        return property_obj

    @staticmethod
    async def create_property(
        db: AsyncSession,
        user: User,
        data: PropertyCreate,
    ) -> Property:

        property_obj = Property(
            user_id=user.id,
            label=data.label,
            address=data.address,
            deposit_amount=data.deposit_amount,
            lease_start_date=data.lease_start_date,
            lease_end_date=data.lease_end_date,
        )

        db.add(property_obj)

        await db.commit()

        await db.refresh(property_obj)

        await track(
            db=db,
            event_name="property_created",
            user_id=user.id,
            properties={
                "property_id": str(property_obj.id),
                "label": property_obj.label,
            },
        )

        logger.info(
            "Property %s created by %s",
            property_obj.id,
            user.id,
        )

        return property_obj

    @staticmethod
    async def list_properties(
        db: AsyncSession,
        user: User,
    ) -> list[Property]:

        result = await db.execute(
            select(Property)
            .where(Property.user_id == user.id)
            .order_by(Property.created_at.desc())
        )

        return list(result.scalars().all())

    @staticmethod
    async def get_property(
        db: AsyncSession,
        property_id: uuid.UUID,
        user: User,
    ) -> Property:

        return await PropertyService.get_owned_property(
            db=db,
            property_id=property_id,
            user=user,
        )

    @staticmethod
    async def update_property(
        db: AsyncSession,
        property_id: uuid.UUID,
        user: User,
        data: PropertyUpdate,
    ) -> Property:

        property_obj = await PropertyService.get_owned_property(
            db=db,
            property_id=property_id,
            user=user,
        )

        updates = data.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(property_obj, field, value)

        db.add(property_obj)

        await db.commit()

        await db.refresh(property_obj)

        logger.info(
            "Property %s updated",
            property_obj.id,
        )

        return property_obj