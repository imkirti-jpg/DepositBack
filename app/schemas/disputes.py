import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel , computed_field
from app.models.dispute import ClaimLabel, NoticeStatus


class NoticeResponse(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    file_url: str | None
    raw_text: str | None
    status: NoticeStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ClaimResponse(BaseModel):
    id: uuid.UUID
    deduction_notice_id: uuid.UUID
    item_description: str
    claimed_amount: Decimal | None
    label: ClaimLabel
    reasoning: str
    evidence_refs: dict
    user_override_label: ClaimLabel | None
    # effective_label is what the frontend should display —
    # user override takes precedence over AI label
    effective_label: ClaimLabel | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_effective(cls, claim) -> "ClaimResponse":
        data = cls.model_validate(claim)
        data.effective_label = claim.user_override_label or claim.label
        return data


class ClaimOverride(BaseModel):
    user_override_label: ClaimLabel