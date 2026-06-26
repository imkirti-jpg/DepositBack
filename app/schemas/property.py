import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator
from app.models.property import PropertyStatus


class PropertyCreate(BaseModel):
    label: str
    address: str | None = None
    deposit_amount: Decimal
    lease_start_date: date | None = None
    lease_end_date: date | None = None

    @field_validator("deposit_amount")
    @classmethod
    def deposit_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Deposit amount must be greater than zero")
        return v

    @field_validator("label")
    @classmethod
    def label_must_not_be_blank(cls, v):
        if not v.strip():
            raise ValueError("Label cannot be blank")
        return v.strip()


class PropertyUpdate(BaseModel):
    label: str | None = None
    address: str | None = None
    deposit_amount: Decimal | None = None
    lease_start_date: date | None = None
    lease_end_date: date | None = None
    status: PropertyStatus | None = None


class PropertyResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    label: str
    address: str | None
    deposit_amount: Decimal
    lease_start_date: date | None
    lease_end_date: date | None
    status: PropertyStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}