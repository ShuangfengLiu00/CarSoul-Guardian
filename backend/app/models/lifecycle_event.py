"""Vehicle lifecycle events — the timeline of a vehicle's digital life.

Every major milestone (purchase, transfer, accident, repair, inspection,
insurance renewal, …) is recorded here, forming the backbone of the
"vehicle digital-life archive" narrative.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database.base import Base

# Use dialect-agnostic JSON so it works on both SQLite and PostgreSQL.
JSONType = SQLiteJSON().with_variant(JSON(), "postgresql")


class VehicleLifecycleEvent(Base):
    """A single point on the vehicle's life timeline."""

    __tablename__ = "vehicle_lifecycle_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    # purchase | transfer | accident | repair | maintenance | inspection
    # | insurance | registration | custom
    event_type: Mapped[str] = mapped_column(String(32), index=True)

    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    event_date: Mapped[date] = mapped_column(Date, index=True)
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ---- Cost / location ----
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # ---- Severity (for accidents / faults) ----
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # info | minor | moderate | major | critical

    # ---- Flexible payload ----
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
