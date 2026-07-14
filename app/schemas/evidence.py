import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.evidence import EvidencePhase


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    phase: EvidencePhase
    room_label: str | None
    file_url: str
    file_hash: str | None
    display_name: str
    category: str
    sort_order: int
    notes: str | None
    mime_type: str | None
    file_size: int | None
    width: int | None
    height: int | None
    captured_at: datetime | None
    deleted_at: datetime | None
    deleted_by: uuid.UUID | None
    created_at: datetime
    uploaded_at: datetime
    thumbnail_url: str | None = None
    full_image_url: str | None = None

    model_config = {"from_attributes": True}


class EvidenceFilters(BaseModel):
    #Query params for GET /evidence
    property_id: uuid.UUID
    phase: EvidencePhase | None = None
    room_label: str | None = None