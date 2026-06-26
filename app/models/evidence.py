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
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )