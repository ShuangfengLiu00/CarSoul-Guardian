"""Vehicle digital state — the real-time "current state" of the vehicle.

A single row per vehicle (unique) that mirrors the live health indicators:
engine / battery / brake / tyre health, overall score, temperature, mileage,
fuel level, location, and a coarse status (GOOD / WARNING / DANGER /
END_OF_LIFE). This is what the digital-twin engine and the AI agent read to
answer "how is the car right now?".

Distinct from `VehicleHealthSnapshot` (a periodic point-in-time assessment)
and `VehicleDigitalTwin` (twin metadata + raw telemetry): the digital state
is the *derived*, human/agent-facing current health summary.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database.base import Base

JSONType = SQLiteJSON().with_variant(JSON(), "postgresql")


class VehicleDigitalState(Base):
    """The real-time current digital state of a single vehicle."""

    __tablename__ = "vehicle_digital_states"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), unique=True, index=True
    )

    # ---- Sub-system health (0-100) ----
    engine_health: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_health: Mapped[float | None] = mapped_column(Float, nullable=True)
    brake_health: Mapped[float | None] = mapped_column(Float, nullable=True)
    tire_health: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_health: Mapped[float | None] = mapped_column(Float, nullable=True)
    electronics_health: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ---- Overall ----
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    # GOOD | WARNING | DANGER | END_OF_LIFE
    status: Mapped[str] = mapped_column(String(30), default="GOOD", index=True)

    # ---- Live telemetry snapshot ----
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)  # ℃
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fuel_level: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # % or kWh remaining
    location: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )  # {"lat": ..., "lng": ..., "name": ...}

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
