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
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceFilters(BaseModel):
    #Query params for GET /evidence
    property_id: uuid.UUID
    phase: EvidencePhase | None = None
    room_label: str | None = None