"""Vehicle trip records — every journey the vehicle makes.

Unlike `VehicleDrivingBehavior` (which is a daily aggregation), a *trip* is a
single point-to-point journey with start/end timestamps, distance, speed
stats, energy consumption, and road condition. Trips form the backbone of the
vehicle's "growth record" timeline (first drive → 10,000 km → first service →
accident → repair → resale).
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


class VehicleTrip(Base):
    """A single driving trip for a vehicle."""

    __tablename__ = "vehicle_trips"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )
    driver_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ---- Distance & speed ----
    distance: Mapped[float] = mapped_column(Float, default=0.0)  # km
    average_speed: Mapped[float | None] = mapped_column(Float, nullable=True)  # km/h
    max_speed: Mapped[float | None] = mapped_column(Float, nullable=True)  # km/h

    # ---- Energy ----
    energy_consumption: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # L (fuel) or kWh (electric)

    # ---- Context ----
    # urban | highway | suburban | mountain | rural
    road_condition: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # sunny | cloudy | rainy | snowy | foggy
    weather: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # ---- Behaviour events during the trip ----
    harsh_acceleration_count: Mapped[int] = mapped_column(Integer, default=0)
    harsh_braking_count: Mapped[int] = mapped_column(Integer, default=0)
    overspeed_count: Mapped[int] = mapped_column(Integer, default=0)

    # ---- Start / end location ----
    start_location: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )  # {"lat": ..., "lng": ..., "name": ...}
    end_location: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )

    notes: Mapped[str | None] = mapped_column(String(256), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
