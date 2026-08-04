"""Lifecycle event service — CRUD for the vehicle life timeline."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lifecycle_event import VehicleLifecycleEvent
from app.schemas.lifecycle_event import LifecycleEventCreate


def list_events(
    db: Session, vehicle_id: int, event_type: str | None = None
) -> list[VehicleLifecycleEvent]:
    stmt = select(VehicleLifecycleEvent).where(
        VehicleLifecycleEvent.vehicle_id == vehicle_id
    )
    if event_type:
        stmt = stmt.where(VehicleLifecycleEvent.event_type == event_type)
    stmt = stmt.order_by(VehicleLifecycleEvent.event_date.desc())
    return list(db.scalars(stmt).all())


def get_event(db: Session, event_id: int) -> VehicleLifecycleEvent | None:
    return db.get(VehicleLifecycleEvent, event_id)


def create_event(
    db: Session, vehicle_id: int, payload: LifecycleEventCreate
) -> VehicleLifecycleEvent:
    event = VehicleLifecycleEvent(**payload.model_dump(), vehicle_id=vehicle_id)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event_id: int) -> bool:
    event = db.get(VehicleLifecycleEvent, event_id)
    if event is None:
        return False
    db.delete(event)
    db.commit()
    return True
