"""Driving behaviour service — daily trip aggregations."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.driving_behavior import VehicleDrivingBehavior
from app.schemas.driving_behavior import DrivingBehaviorCreate


def list_behaviors(
    db: Session,
    vehicle_id: int,
    days: int = 30,
) -> list[VehicleDrivingBehavior]:
    cutoff = date.today() - timedelta(days=days)
    stmt = (
        select(VehicleDrivingBehavior)
        .where(
            VehicleDrivingBehavior.vehicle_id == vehicle_id,
            VehicleDrivingBehavior.record_date >= cutoff,
        )
        .order_by(VehicleDrivingBehavior.record_date.desc())
    )
    return list(db.scalars(stmt).all())


def get_behavior(db: Session, behavior_id: int) -> VehicleDrivingBehavior | None:
    return db.get(VehicleDrivingBehavior, behavior_id)


def create_behavior(
    db: Session, vehicle_id: int, payload: DrivingBehaviorCreate
) -> VehicleDrivingBehavior:
    behavior = VehicleDrivingBehavior(
        **payload.model_dump(), vehicle_id=vehicle_id
    )
    db.add(behavior)
    db.commit()
    db.refresh(behavior)
    return behavior


def get_behavior_summary(
    db: Session, vehicle_id: int, days: int = 30
) -> dict:
    """Aggregate driving behaviour over the given period."""
    records = list_behaviors(db, vehicle_id, days)
    if not records:
        return {
            "total_distance": 0.0,
            "total_duration": 0,
            "avg_safety_score": None,
            "avg_eco_score": None,
            "total_harsh_events": 0,
            "total_fuel": 0.0,
            "trip_count": 0,
        }

    total_distance = sum(r.total_distance for r in records)
    total_duration = sum(r.total_duration for r in records)
    safety_scores = [r.safety_score for r in records if r.safety_score is not None]
    eco_scores = [r.eco_score for r in records if r.eco_score is not None]
    harsh = sum(
        r.harsh_acceleration_count
        + r.harsh_braking_count
        + r.sharp_turn_count
        + r.overspeed_count
        for r in records
    )
    total_fuel = sum(r.fuel_consumption or 0 for r in records)

    return {
        "total_distance": round(total_distance, 1),
        "total_duration": total_duration,
        "avg_safety_score": round(sum(safety_scores) / len(safety_scores))
        if safety_scores
        else None,
        "avg_eco_score": round(sum(eco_scores) / len(eco_scores))
        if eco_scores
        else None,
        "total_harsh_events": harsh,
        "total_fuel": round(total_fuel, 2),
        "trip_count": sum(r.trip_count for r in records),
    }


def delete_behavior(db: Session, behavior_id: int) -> bool:
    behavior = db.get(VehicleDrivingBehavior, behavior_id)
    if behavior is None:
        return False
    db.delete(behavior)
    db.commit()
    return True
