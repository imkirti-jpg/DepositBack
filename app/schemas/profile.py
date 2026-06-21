from pydantic import BaseModel
from uuid import UUID

class ProfileResponse(BaseModel):
    id: UUID
    full_name: str | None
    city: str | None


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    city: str | None = None