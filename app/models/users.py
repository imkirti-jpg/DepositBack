from datetime import datetime
import uuid
from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy import DateTime
from sqlalchemy import func

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.database import Base

class User(Base):
    __tablename__ = "users"
    id : Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    full_name : Mapped[str] = mapped_column(String(255), nullable=True)
    city : Mapped[str] = mapped_column(String(255), nullable=True)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id : Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey("profiles.id"),unique=True)
    email_enabled : Mapped[bool] = mapped_column(Boolean, default=True)
    sms_enabled : Mapped[bool] = mapped_column(Boolean, default=False)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)