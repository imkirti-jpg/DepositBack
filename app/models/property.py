import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, Numeric, String, Text, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class PropertyStatus(str, enum.Enum):
    active = "active"
    resolved = "resolved"


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)          # e.g. "2BHK Indiranagar"
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    deposit_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    lease_start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    lease_end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    status: Mapped[PropertyStatus] = mapped_column(Enum(PropertyStatus, name="property_status"),nullable=False,default=PropertyStatus.active)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False,  default=lambda: datetime.now(timezone.utc),onupdate=lambda: datetime.now(timezone.utc))