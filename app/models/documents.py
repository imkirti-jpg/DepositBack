import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class DocType(str, enum.Enum):
    message = "message"             # short-form WhatsApp / email draft
    formal_letter = "formal_letter" # full demand letter with legal language


class DocStatus(str, enum.Enum):
    processing = "processing"
    draft = "draft"       # AI generation done, ready for user to edit
    sent = "sent"         # user marked as sent
    failed = "failed"


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False, index=True
    )
    deduction_notice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deduction_notices.id"), nullable=True, index=True
    )
    doc_type: Mapped[DocType] = mapped_column(
        Enum(DocType, name="doc_type"), nullable=False
    )
    status: Mapped[DocStatus] = mapped_column(
        Enum(DocStatus, name="doc_status"), nullable=False, default=DocStatus.processing
    )
    ai_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    edited_content: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="User's edited version. Display this over ai_draft when present."
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )