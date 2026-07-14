import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class EvidencePhase(str, enum.Enum):
    move_in = "move_in"
    move_out = "move_out"


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False, index=True
    )
    phase: Mapped[EvidencePhase] = mapped_column(
        Enum(EvidencePhase, name="evidence_phase"), nullable=False
    )
    room_label: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Free text — no normalization at MVP. e.g. 'master bedroom', 'kitchen'"
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False, default="Evidence File", server_default="Evidence File")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="damage", server_default="damage", index=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    width: Mapped[int | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )