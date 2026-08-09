"""Sensor data service — IoT telemetry ingestion and time-series queries."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.sensor_data import VehicleSensorData
from app.schemas.sensor_data import (
    SensorDataBatchCreate,
    SensorDataCreate,
    SensorDataOut,
    SensorSeriesOut,
    SensorSeriesPoint,
)


def list_readings(
    db: Session,
    vehicle_id: int,
    sensor_type: str | None = None,
    limit: int = 200,
    since: datetime | None = None,
) -> list[VehicleSensorData]:
    stmt = (
        select(VehicleSensorData)
        .where(VehicleSensorData.vehicle_id == vehicle_id)
        .order_by(VehicleSensorData.created_at.desc())
        .limit(limit)
    )
    if sensor_type:
        stmt = stmt.where(VehicleSensorData.sensor_type == sensor_type)
    if since:
        stmt = stmt.where(VehicleSensorData.created_at >= since)
    return list(db.scalars(stmt).all())


def create_reading(
    db: Session, vehicle_id: int, payload: SensorDataCreate
) -> VehicleSensorData:
    row = VehicleSensorData(vehicle_id=vehicle_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_readings_batch(
    db: Session, vehicle_id: int, payload: SensorDataBatchCreate
) -> list[VehicleSensorData]:
    rows = [
        VehicleSensorData(vehicle_id=vehicle_id, **r.model_dump())
        for r in payload.readings
    ]
    db.add_all(rows)
    db.commit()
    for r in rows:
        db.refresh(r)
    return rows


def get_series(
    db: Session,
    vehicle_id: int,
    sensor_type: str,
    hours: int = 24,
) -> SensorSeriesOut:
    """Return a time-series for one sensor type over the last N hours."""
    since = datetime.utcnow() - timedelta(hours=hours)
    rows = list(
        db.scalars(
            select(VehicleSensorData)
            .where(
                VehicleSensorData.vehicle_id == vehicle_id,
                VehicleSensorData.sensor_type == sensor_type,
                VehicleSensorData.created_at >= since,
            )
            .order_by(VehicleSensorData.created_at.asc())
        ).all()
    )
    unit = rows[0].unit if rows else None
    return SensorSeriesOut(
        sensor_type=sensor_type,
        unit=unit,
        points=[
            SensorSeriesPoint(timestamp=r.created_at, value=r.sensor_value)
            for r in rows
        ],
    )


def latest_reading(
    db: Session, vehicle_id: int, sensor_type: str
) -> VehicleSensorData | None:
    """Return the most recent reading for one sensor type, or None."""
    return db.scalar(
        select(VehicleSensorData)
        .where(
            VehicleSensorData.vehicle_id == vehicle_id,
            VehicleSensorData.sensor_type == sensor_type,
        )
        .order_by(VehicleSensorData.created_at.desc(), VehicleSensorData.id.desc())
        .limit(1)
    )


def list_sensor_types(db: Session, vehicle_id: int) -> list[str]:
    rows = db.scalars(
        select(VehicleSensorData.sensor_type)
        .where(VehicleSensorData.vehicle_id == vehicle_id)
        .distinct()
        .order_by(VehicleSensorData.sensor_type.asc())
    ).all()
    return list(rows)


def count(db: Session, vehicle_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(VehicleSensorData)
        .where(VehicleSensorData.vehicle_id == vehicle_id)
    ) or 0
