from fastapi import APIRouter, Depends
import supabase
from app.db.database import get_db
from app.schemas.profile import (ProfileResponse,ProfileUpdate)
from app.services.profile_service import ProfileService
from app.dependency.auths import get_current_user
from app.core.config import settings

router = APIRouter(
    prefix="/me",
    tags=["Profile"]
)

@router.get("",response_model=ProfileResponse)
async def get_me(
    current_user=Depends(get_current_user)
):
    return current_user


@router.put("", response_model=ProfileResponse)
async def update_me(
    payload: ProfileUpdate,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):
    return await ProfileService.update_profile(
        db,
        current_user,
        payload
    )

#temp
from supabase import create_client

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_ANON_KEY

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

response = supabase.auth.sign_in_with_password(
    {
        "email": "kirtisingh239on@gmail.com",
        "password": "hello098"
    }
)

print(response.session.access_token)

