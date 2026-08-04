"""Trip service — per-journey CRUD and aggregation."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.trip import VehicleTrip
from app.schemas.trip import TripCreate, TripSummary


def list_trips(
    db: Session, vehicle_id: int, limit: int = 50
) -> list[VehicleTrip]:
    stmt = (
        select(VehicleTrip)
        .where(VehicleTrip.vehicle_id == vehicle_id)
        .order_by(VehicleTrip.start_time.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def get_trip(db: Session, trip_id: int) -> VehicleTrip | None:
    return db.get(VehicleTrip, trip_id)


def create_trip(
    db: Session, vehicle_id: int, payload: TripCreate
) -> VehicleTrip:
    trip = VehicleTrip(vehicle_id=vehicle_id, **payload.model_dump())
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def delete_trip(db: Session, trip_id: int) -> bool:
    trip = db.get(VehicleTrip, trip_id)
    if trip is None:
        return False
    db.delete(trip)
    db.commit()
    return True


def get_summary(
    db: Session, vehicle_id: int, days: int = 30
) -> TripSummary:
    """Aggregate trip statistics over the last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    rows = list(
        db.scalars(
            select(VehicleTrip)
            .where(
                VehicleTrip.vehicle_id == vehicle_id,
                VehicleTrip.start_time >= since,
            )
            .order_by(VehicleTrip.start_time.asc())
        ).all()
    )
    if not rows:
        return TripSummary()

    total_distance = sum(r.distance or 0 for r in rows)
    total_energy = sum(r.energy_consumption or 0 for r in rows)
    total_duration_h = 0.0
    for r in rows:
        if r.end_time and r.start_time:
            total_duration_h += (r.end_time - r.start_time).total_seconds() / 3600

    speeds = [r.average_speed for r in rows if r.average_speed]
    harsh = sum(
        (r.harsh_acceleration_count or 0)
        + (r.harsh_braking_count or 0)
        + (r.overspeed_count or 0)
        for r in rows
    )

    return TripSummary(
        trip_count=len(rows),
        total_distance=round(total_distance, 1),
        total_duration_hours=round(total_duration_h, 2),
        total_energy=round(total_energy, 2),
        avg_speed=round(sum(speeds) / len(speeds), 1) if speeds else None,
        harsh_events=harsh,
        first_trip_time=rows[0].start_time,
        last_trip_time=rows[-1].start_time,
    )


def count(db: Session, vehicle_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(VehicleTrip)
        .where(VehicleTrip.vehicle_id == vehicle_id)
    ) or 0
