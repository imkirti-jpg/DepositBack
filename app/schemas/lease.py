import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.lease import LeaseStatus


class LeaseResponse(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    file_url: str
    extracted_fields: dict | None
    status: LeaseStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaseFieldsUpdate(BaseModel):
    extracted_fields: dict