"""Vehicle health snapshots and per-item risk breakdown.

A *snapshot* captures the overall health score at a point in time, plus
individual *items* (engine, brakes, tyres, battery, body, electronics)
each with their own score, level, and recommendation.

The latest snapshot for a vehicle is what powers the Dashboard health
gauge and the agent's `get_health_score` tool.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database.base import Base

JSONType = SQLiteJSON().with_variant(JSON(), "postgresql")


class VehicleHealthSnapshot(Base):
    """A periodic health assessment for a vehicle."""

    __tablename__ = "vehicle_health_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    health_score: Mapped[int] = mapped_column(Integer)  # 0-100
    mileage: Mapped[int] = mapped_column(Integer)

    # ---- Sub-scores (nullable — not all vehicles have all subsystems) ----
    engine_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    brake_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tire_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    battery_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    electronics_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---- Source / trigger ----
    source: Mapped[str] = mapped_column(String(32), default="manual")
    # manual | obd | scheduled | agent

    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )


class VehicleHealthItem(Base):
    """An individual check-item within a health snapshot."""

    __tablename__ = "vehicle_health_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("vehicle_health_snapshots.id", ondelete="CASCADE"), index=True
    )
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), index=True
    )

    # engine | brake | tire | battery | body | electronics | fluid | other
    category: Mapped[str] = mapped_column(String(32))
    item_name: Mapped[str] = mapped_column(String(64))

    # ok | info | warning | critical
    level: Mapped[str] = mapped_column(String(16))
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100

    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
