from app.services.property_service import PropertyService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.property import Property
from app.models.users import User
from app.schemas.property import PropertyCreate, PropertyUpdate , PropertyResponse
from app.services.analytics import track
import uuid
from fastapi import Depends, HTTPException, status , APIRouter
from sqlalchemy import select
from app.dependency.auths import get_current_user
from app.db.database import get_db

router = APIRouter(prefix="/properties", tags=["properties"])

async def get_owned_property(
    db: AsyncSession,
    property_id: uuid.UUID,
    user: User,
) -> Property:

    result = await db.execute(
        select(Property).where(
            Property.id == property_id,
            Property.user_id == user.id,
            Property.deleted_at.is_(None),
        )
    )

    prop = result.scalar_one_or_none()

    if prop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    return prop

async def owned_property(
    property_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_owned_property(
        db=db,
        property_id=property_id,
        user=current_user,
    )

@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_property_route(
    body: PropertyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await PropertyService.create_property(db=db,user=current_user,data=body)


@router.get(
    "",
    response_model=list[PropertyResponse],
)
async def list_properties_route(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await PropertyService.list_properties(db=db,user=current_user)


@router.get("/{property_id}",response_model=PropertyResponse)
async def get_property(prop: Property = Depends(owned_property)):
    return prop


@router.put("/{property_id}",response_model=PropertyResponse)
async def update_property_route(
    property_id: uuid.UUID,
    body: PropertyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await PropertyService.update_property(db=db,property_id=property_id,user=current_user,data=body)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property_route(
    property_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await PropertyService.delete_property(db=db, property_id=property_id, user=current_user)
    return