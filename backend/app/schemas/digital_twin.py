"""Digital twin schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DigitalTwinBase(BaseModel):
    model_version: str = "1.0"
    model_url: str | None = None
    telemetry: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    sync_status: str = "pending"
    sync_frequency: str = "realtime"
    notes: str | None = None


class DigitalTwinCreate(DigitalTwinBase):
    pass


class DigitalTwinUpdate(BaseModel):
    model_version: str | None = None
    model_url: str | None = None
    telemetry: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    sync_status: str | None = None
    sync_frequency: str | None = None
    notes: str | None = None


class DigitalTwinOut(DigitalTwinBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    last_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
