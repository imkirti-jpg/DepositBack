from fastapi import APIRouter, Depends
from app.dependency.auths import get_current_user
from app.schemas.preferences import PreferencesResponse 
from app.db.database import get_db
from app.services.preferences_service import PreferenceService
from app.schemas.preferences import PreferencesUpdate

router = APIRouter(
    prefix="/preferences",
    tags=["Preferences"]
)

@router.get(
    "",
    response_model=PreferencesResponse
)
async def get_preferences(
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):

    return await PreferenceService.get_preferences(
        db,
        current_user.id
    )


@router.put(
    "",
    response_model=PreferencesResponse
)
async def update_preferences(
    payload: PreferencesUpdate,
    current_user=Depends(get_current_user),
    db=Depends(get_db)
):

    preference = await PreferenceService.get_preferences(
        db,
        current_user.id
    )

    return await PreferenceService.update_preferences(
        db,
        preference,
        payload
    )