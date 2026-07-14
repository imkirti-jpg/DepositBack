import uuid
from datetime import datetime
from pydantic import BaseModel, computed_field
from app.models.documents import DocType, DocStatus


class DocumentCreate(BaseModel):
    property_id: uuid.UUID
    deduction_notice_id: uuid.UUID
    doc_type: DocType


class DocumentUpdate(BaseModel):
    edited_content: str


class DocumentResponse(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    deduction_notice_id: uuid.UUID | None
    doc_type: DocType
    status: DocStatus
    error_message: str | None = None
    ai_draft: str | None
    edited_content: str | None
    sent_at: datetime | None
    created_at: datetime

    # Always display content — edited version takes precedence over AI draft
    @computed_field
    @property
    def display_content(self) -> str | None:
        return self.edited_content or self.ai_draft

    model_config = {"from_attributes": True}