"""Driving-behavior records — daily trip aggregations per vehicle.

Each row summarises one day of driving: distance, duration, speed stats,
behaviour scores (safety / eco), and counts of harsh events.  This feeds
the agent's driving-style analysis and the Dashboard behaviour panel.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class VehicleDrivingBehavior(Base):
    """A daily driving-behaviour summary for a vehicle."""

    __tablename__ = "vehicle_driving_behaviors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    record_date: Mapped[date] = mapped_column(Date, index=True)

    # ---- Trip stats ----
    trip_count: Mapped[int] = mapped_column(Integer, default=0)
    total_distance: Mapped[float] = mapped_column(Float, default=0.0)  # km
    total_duration: Mapped[int] = mapped_column(Integer, default=0)  # minutes
    avg_speed: Mapped[float | None] = mapped_column(Float, nullable=True)  # km/h
    max_speed: Mapped[float | None] = mapped_column(Float, nullable=True)  # km/h

    # ---- Behaviour scores (0-100) ----
    safety_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eco_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ---- Event counts ----
    harsh_acceleration_count: Mapped[int] = mapped_column(Integer, default=0)
    harsh_braking_count: Mapped[int] = mapped_column(Integer, default=0)
    sharp_turn_count: Mapped[int] = mapped_column(Integer, default=0)
    overspeed_count: Mapped[int] = mapped_column(Integer, default=0)
    idle_duration: Mapped[int] = mapped_column(Integer, default=0)  # minutes

    # ---- Energy ----
    fuel_consumption: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # L or kWh
    energy_efficiency: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # km/L or km/kWh

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
