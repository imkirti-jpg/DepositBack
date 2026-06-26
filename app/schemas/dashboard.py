import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from app.models.dispute import ClaimLabel
from app.models.documents import DocType, DocStatus
from app.models.lease import LeaseStatus
from app.models.dispute import NoticeStatus
from app.models.property import PropertyStatus


class ClaimSummary(BaseModel):
    id: uuid.UUID
    item_description: str
    claimed_amount: Decimal | None
    effective_label: ClaimLabel

    model_config = {"from_attributes": True}


class DocumentSummary(BaseModel):
    id: uuid.UUID
    doc_type: DocType
    status: DocStatus
    sent_at: datetime | None

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    # Property
    property_id: uuid.UUID
    property_label: str
    property_status: PropertyStatus
    deposit_amount: Decimal

    # Lease
    lease_id: uuid.UUID | None
    lease_status: LeaseStatus | None

    # Evidence counts
    move_in_evidence_count: int
    move_out_evidence_count: int

    # Notice
    notice_id: uuid.UUID | None
    notice_status: NoticeStatus | None

    # Claims
    claims: list[ClaimSummary]
    total_supported_amount: Decimal    # sum of supported claim amounts
    total_disputed_amount: Decimal     # sum of weak + unsupported + unclear amounts
    total_unquantified_count: int      # disputed claims with no amount stated

    # Documents
    documents: list[DocumentSummary]

    # Derived state — always computed, never stored
    next_action: str