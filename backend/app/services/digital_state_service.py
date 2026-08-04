"""Digital state service — real-time vehicle current state.

One row per vehicle (unique). Provides get / upsert / patch semantics.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.digital_state import VehicleDigitalState
from app.schemas.digital_state import DigitalStateCreate, DigitalStateUpdate


def get_state(db: Session, vehicle_id: int) -> VehicleDigitalState | None:
    return db.scalar(
        select(VehicleDigitalState).where(
            VehicleDigitalState.vehicle_id == vehicle_id
        )
    )


def upsert_state(
    db: Session, vehicle_id: int, payload: DigitalStateCreate
) -> VehicleDigitalState:
    """Create or replace the digital state for a vehicle."""
    state = get_state(db, vehicle_id)
    if state is None:
        state = VehicleDigitalState(vehicle_id=vehicle_id, **payload.model_dump())
        db.add(state)
    else:
        for key, val in payload.model_dump().items():
            setattr(state, key, val)
    db.commit()
    db.refresh(state)
    return state


def patch_state(
    db: Session, vehicle_id: int, payload: DigitalStateUpdate
) -> VehicleDigitalState | None:
    state = get_state(db, vehicle_id)
    if state is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    for key, val in data.items():
        setattr(state, key, val)
    db.commit()
    db.refresh(state)
    return state


def delete_state(db: Session, vehicle_id: int) -> bool:
    state = get_state(db, vehicle_id)
    if state is None:
        return False
    db.delete(state)
    db.commit()
    return True


def derive_status(overall_score: float | None) -> str:
    """Map an overall score to a coarse status label."""
    if overall_score is None:
        return "GOOD"
    if overall_score >= 80:
        return "GOOD"
    if overall_score >= 60:
        return "WARNING"
    if overall_score >= 40:
        return "DANGER"
    return "END_OF_LIFE"


def update_from_components(
    db: Session,
    vehicle_id: int,
    engine: float | None = None,
    battery: float | None = None,
    brake: float | None = None,
    tire: float | None = None,
    body: float | None = None,
    electronics: float | None = None,
    temperature: float | None = None,
    mileage: int | None = None,
    fuel_level: float | None = None,
    location: dict[str, Any] | None = None,
) -> VehicleDigitalState:
    """Convenience: patch only the provided fields and recompute overall."""
    state = get_state(db, vehicle_id)
    if state is None:
        state = VehicleDigitalState(vehicle_id=vehicle_id)
        db.add(state)

    if engine is not None:
        state.engine_health = engine
    if battery is not None:
        state.battery_health = battery
    if brake is not None:
        state.brake_health = brake
    if tire is not None:
        state.tire_health = tire
    if body is not None:
        state.body_health = body
    if electronics is not None:
        state.electronics_health = electronics
    if temperature is not None:
        state.temperature = temperature
    if mileage is not None:
        state.mileage = mileage
    if fuel_level is not None:
        state.fuel_level = fuel_level
    if location is not None:
        state.location = location

    # Recompute overall from available sub-scores (simple mean).
    scores = [
        s
        for s in (state.engine_health, state.battery_health,
                  state.brake_health, state.tire_health,
                  state.body_health, state.electronics_health)
        if s is not None
    ]
    if scores:
        state.overall_score = round(sum(scores) / len(scores), 1)
        state.status = derive_status(state.overall_score)

    db.commit()
    db.refresh(state)
    return state
