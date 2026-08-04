"""Vehicle sensor data — high-frequency IoT telemetry time-series.

Each row is a single sensor reading at a point in time (engine temperature,
battery voltage, tyre pressure, …). This is the raw input stream that feeds
the digital-twin real-time state and the AI perception/diagnosis agents.

In production this table is backed by a TimescaleDB hypertable; in dev it is
a plain table on SQLite.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database.base import Base

# Dialect-agnostic JSON so it works on both SQLite (dev) and PostgreSQL.
JSONType = SQLiteJSON().with_variant(JSON(), "postgresql")


class VehicleSensorData(Base):
    """A single IoT sensor reading for a vehicle."""

    __tablename__ = "vehicle_sensor_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    # engine_temp | battery_voltage | tire_pressure | coolant_temp |
    # rpm | speed | fuel_level | oil_pressure | intake_air_temp | ...
    sensor_type: Mapped[str] = mapped_column(String(50), index=True)
    sensor_value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Optional metadata (e.g. which wheel for tyre pressure)
    # {"position": "FL"} / {"channel": 1}
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
