"""Vehicle digital-twin metadata.

One row per vehicle (unique).  Stores the twin model reference, real-time
telemetry payload, configuration, and sync status — the bridge between
the physical vehicle and its AI-mirror in the cloud.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database.base import Base

JSONType = SQLiteJSON().with_variant(JSON(), "postgresql")


class VehicleDigitalTwin(Base):
    """Digital-twin state for a single vehicle."""

    __tablename__ = "vehicle_digital_twins"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), unique=True, index=True
    )

    model_version: Mapped[str] = mapped_column(String(32), default="1.0")
    model_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ---- Real-time telemetry snapshot ----
    telemetry: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )

    # ---- Twin configuration ----
    config: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)

    # ---- Sync status ----
    # pending | syncing | synced | error
    sync_status: Mapped[str] = mapped_column(String(16), default="pending")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # realtime | hourly | daily
    sync_frequency: Mapped[str] = mapped_column(String(16), default="realtime")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
