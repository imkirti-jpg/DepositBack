import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    event_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )