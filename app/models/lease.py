import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class LeaseStatus(str, enum.Enum):
    processing = "processing"
    needs_review = "needs_review"   # extraction done but ≥1 low-confidence field
    confirmed = "confirmed"          # all fields confirmed (by AI or user)
    failed = "failed"                # extraction failed after retry


class Lease(Base):
    __tablename__ = "leases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False, index=True)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[LeaseStatus] = mapped_column(Enum(LeaseStatus, name="lease_status"),nullable=False,default=LeaseStatus.processing)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )