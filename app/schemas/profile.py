from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

class ProfileResponse(BaseModel):
    id: UUID
    full_name: str | None
    city: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

class ProfileUpdate(BaseModel):
    full_name: str | None = None
    city: str | None = None