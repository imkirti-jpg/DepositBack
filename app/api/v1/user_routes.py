from fastapi import APIRouter, Depends
import supabase
from app.services.analytics import track
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.profile import (ProfileResponse,ProfileUpdate)
from app.services.profile_service import ProfileService
from app.dependency.auths import get_current_user
from app.core.config import settings
from app.models.users import User

router = APIRouter(prefix="/me", tags=["Profile"])

@router.get("", response_model=ProfileResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("", response_model=ProfileResponse)
async def update_me(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.city is not None:
        current_user.city = body.city

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    await track(db, "profile_updated", user_id=current_user.id, properties={"city": current_user.city})
    return current_user


#temp
from supabase import create_client

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_ANON_KEY

supabase = create_client(SUPABASE_URL,SUPABASE_KEY)

response = supabase.auth.sign_in_with_password(
    {
        "email": "kirtisingh239on@gmail.com",
        "password": "hello098"
    }
)
print(response.session.access_token)
