import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class NoticeStatus(str, enum.Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ClaimLabel(str, enum.Enum):
    supported = "supported"       # evidence backs the deduction
    weak = "weak"                 # deduction is questionable
    unsupported = "unsupported"   # no basis found in lease or evidence
    unclear = "unclear"           # not enough info to assess


class DeductionNotice(Base):
    __tablename__ = "deduction_notices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False, index=True
    )
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[NoticeStatus] = mapped_column(
        Enum(NoticeStatus, name="notice_status"),
        nullable=False,
        default=NoticeStatus.processing,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deduction_notice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deduction_notices.id"), nullable=False, index=True
    )
    item_description: Mapped[str] = mapped_column(Text, nullable=False)
    claimed_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    label: Mapped[ClaimLabel] = mapped_column(
        Enum(ClaimLabel, name="claim_label"), nullable=False
    )
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    # Array of evidence UUIDs and/or lease clause references that support the label
    evidence_refs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # User can override the AI label — both are stored, override never erases original
    user_override_label: Mapped[ClaimLabel | None] = mapped_column(
        Enum(ClaimLabel, name="claim_label"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )