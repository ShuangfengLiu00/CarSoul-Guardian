"""Ownership record schemas."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class OwnershipRecordBase(BaseModel):
    owner_id: int | None = None
    owner_name: str | None = Field(None, max_length=64)
    start_date: date = Field(..., description="开始日期")
    end_date: date | None = None
    transfer_type: str = "purchase"
    purchase_price: float | None = Field(None, ge=0)
    sale_price: float | None = Field(None, ge=0)
    mileage_at_transfer: int | None = Field(None, ge=0)
    notes: str | None = None


class OwnershipRecordCreate(OwnershipRecordBase):
    pass


class OwnershipRecordOut(OwnershipRecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    created_at: datetime


class OwnershipRecordList(BaseModel):
    items: list[OwnershipRecordOut]
    total: int = 0
