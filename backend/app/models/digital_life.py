"""Digital Life Engine models — TASK007-V2.

Defines the 9 ORM models that form the Vehicle Digital Life Engine:

  1. VehicleIdentity         — vehicle_identity        (数字身份)
  2. VehicleLifeState         — vehicle_life_state      (生命状态)
  3. VehicleHealthMetrics     — vehicle_health_metrics  (细分健康)
  4. VehicleSensorStream      — vehicle_sensor_stream  (传感器时间序列)
  5. VehicleLifeEvent         — vehicle_life_event      (生命周期事件 ⭐)
  6. VehicleMemory            — vehicle_memory          (记忆系统 ⭐)
  7. DriverProfile            — driver_profile          (驾驶人格模型)
  8. VehiclePrediction        — vehicle_prediction     (AI预测结果)
  9. VehicleSoulScoreHistory  — vehicle_soul_score_history (VSS历史)

All tables reference `vehicles` as the root entity, complementing the
existing TASK007 digital-life archive tables.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

# Use JSONB on PostgreSQL, JSON on SQLite (for dev fallback).
_JSONType = JSONB().with_variant(JSON(), "sqlite")

# Use BigInteger on PostgreSQL, Integer on SQLite (so autoincrement works).
_BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


class VehicleIdentity(Base):
    """车辆数字身份 — 出生证明与灵魂ID."""

    __tablename__ = "vehicle_identity"

    id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )

    vehicle_uuid: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    vin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    production_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    vehicle_class: Mapped[str | None] = mapped_column(String(50), nullable=True)

    owner_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    birth_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VehicleLifeState(Base):
    """车辆生命状态 — 当前生命体征快照."""

    __tablename__ = "vehicle_life_state"

    id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )

    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    life_stage: Mapped[str] = mapped_column(String(30), default="NEW", nullable=False)
    mileage: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    vehicle_age_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    energy_health: Mapped[float | None] = mapped_column(Float, nullable=True)
    mechanical_health: Mapped[float | None] = mapped_column(Float, nullable=True)
    software_health: Mapped[float | None] = mapped_column(Float, nullable=True)

    soul_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class VehicleHealthMetrics(Base):
    """车辆健康指标 — 组件级细分健康."""

    __tablename__ = "vehicle_health_metrics"

    id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    component: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    wear_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)

    record_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class VehicleSensorStream(Base):
    """车辆传感器时间序列 — 高频遥测数据流."""

    __tablename__ = "vehicle_sensor_stream"

    id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    sensor_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    meta: Mapped[dict[str, Any] | None] = mapped_column(_JSONType, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class VehicleLifeEvent(Base):
    """车辆生命事件 ⭐核心 — 区别普通车机的叙事表."""

    __tablename__ = "vehicle_life_event"

    id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    importance: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    mileage: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(_JSONType, nullable=True)

    event_time: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VehicleMemory(Base):
    """车辆记忆系统 ⭐ — 让AI拥有上下文."""

    __tablename__ = "vehicle_memory"

    id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    memory_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    emotion_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    importance: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    source: Mapped[str] = mapped_column(String(50), default="system", nullable=False)
    meta_data: Mapped[dict[str, Any] | None] = mapped_column(_JSONType, nullable=True)

    created_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )


class DriverProfile(Base):
    """驾驶人格模型 — 车辆对车主驾驶风格的认知."""

    __tablename__ = "driver_profile"

    id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )

    driver_style: Mapped[str] = mapped_column(String(50), default="balanced", nullable=False)
    aggressive_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    comfort_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    eco_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    total_trips: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_distance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_duration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_harsh_events: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    preferred_speed_range: Mapped[str | None] = mapped_column(String(30), nullable=True)
    preferred_driving_time: Mapped[str | None] = mapped_column(String(30), nullable=True)
    preferred_road_type: Mapped[str | None] = mapped_column(String(30), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class VehiclePrediction(Base):
    """AI预测结果 — 未来风险与维护预测."""

    __tablename__ = "vehicle_prediction"

    id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    target_component: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    prediction: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    predicted_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    predicted_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    actual_outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)

    prediction_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class VehicleSoulScoreHistory(Base):
    """VSS 灵魂指数历史 — 追踪车辆灵魂的成长轨迹."""

    __tablename__ = "vehicle_soul_score_history"

    id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    soul_score: Mapped[float] = mapped_column(Float, nullable=False)
    health_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    memory_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    maintenance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    driving_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )

