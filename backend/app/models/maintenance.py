"""Maintenance records (actual work done) and schedules (planned work).

*Records* are historical — each entry is a completed service/repair.
*Schedules* are forward-looking rules: "every N km or M days, do X".

The service layer computes `next_due_*` on schedules by comparing
against the vehicle's current mileage and the last record.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database.base import Base

JSONType = SQLiteJSON().with_variant(JSON(), "postgresql")


class VehicleMaintenanceRecord(Base):
    """A completed maintenance / repair event."""

    __tablename__ = "vehicle_maintenance_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    # routine | repair | emergency | inspection | recall
    maintenance_type: Mapped[str] = mapped_column(String(32))
    # 机油更换 | 刹车片 | 轮胎 | 电池 | 滤芯 | …
    category: Mapped[str] = mapped_column(String(64))

    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    maintenance_date: Mapped[date] = mapped_column(Date, index=True)
    mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ---- Cost ----
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ---- Service provider ----
    service_provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    technician: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ---- Parts used (flexible JSON list) ----
    parts: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONType, nullable=True
    )  # [{name, quantity, unit_price}]

    # ---- Next-due hint ----
    next_maintenance_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_maintenance_mileage: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VehicleMaintenanceSchedule(Base):
    """A recurring maintenance rule for a vehicle."""

    __tablename__ = "vehicle_maintenance_schedules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    item_name: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(64))

    # ---- Trigger interval (either or both) ----
    interval_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ---- Last performed (denormalised for quick lookup) ----
    last_mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ---- Computed next-due (updated by service layer) ----
    next_due_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # low | medium | high
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    # pending | due | overdue | done | paused
    status: Mapped[str] = mapped_column(String(16), default="pending")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
