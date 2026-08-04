"""Maintenance service — records (history) + schedules (planned).

Schedules auto-recompute their `next_due_*` and `status` whenever they
are listed or when a new record is added that matches the schedule's
category.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.maintenance import (
    VehicleMaintenanceRecord,
    VehicleMaintenanceSchedule,
)
from app.models.vehicle import Vehicle
from app.schemas.maintenance import (
    MaintenanceRecordCreate,
    MaintenanceScheduleCreate,
)


# ---- Records ----

def list_records(
    db: Session, vehicle_id: int, limit: int = 50
) -> list[VehicleMaintenanceRecord]:
    stmt = (
        select(VehicleMaintenanceRecord)
        .where(VehicleMaintenanceRecord.vehicle_id == vehicle_id)
        .order_by(VehicleMaintenanceRecord.maintenance_date.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def get_record(db: Session, record_id: int) -> VehicleMaintenanceRecord | None:
    return db.get(VehicleMaintenanceRecord, record_id)


def create_record(
    db: Session, vehicle_id: int, payload: MaintenanceRecordCreate
) -> VehicleMaintenanceRecord:
    record = VehicleMaintenanceRecord(
        **payload.model_dump(), vehicle_id=vehicle_id
    )
    db.add(record)
    db.flush()

    # Update matching schedules' last_mileage / last_date
    schedules = list(
        db.scalars(
            select(VehicleMaintenanceSchedule).where(
                VehicleMaintenanceSchedule.vehicle_id == vehicle_id,
                VehicleMaintenanceSchedule.category == payload.category,
            )
        ).all()
    )
    for sched in schedules:
        sched.last_mileage = payload.mileage or sched.last_mileage
        sched.last_date = payload.maintenance_date
        _recompute_schedule(sched, db.get(Vehicle, vehicle_id))

    # Also create a lifecycle event for this maintenance
    from app.models.lifecycle_event import VehicleLifecycleEvent

    event = VehicleLifecycleEvent(
        vehicle_id=vehicle_id,
        event_type="maintenance",
        title=payload.title,
        description=payload.description,
        event_date=payload.maintenance_date,
        mileage=payload.mileage,
        cost=payload.cost,
        location=payload.service_provider,
    )
    db.add(event)

    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record_id: int) -> bool:
    record = db.get(VehicleMaintenanceRecord, record_id)
    if record is None:
        return False
    db.delete(record)
    db.commit()
    return True


# ---- Schedules ----

def list_schedules(
    db: Session, vehicle_id: int
) -> list[VehicleMaintenanceSchedule]:
    stmt = (
        select(VehicleMaintenanceSchedule)
        .where(VehicleMaintenanceSchedule.vehicle_id == vehicle_id)
        .order_by(VehicleMaintenanceSchedule.priority.desc())
    )
    schedules = list(db.scalars(stmt).all())
    vehicle = db.get(Vehicle, vehicle_id)
    for sched in schedules:
        _recompute_schedule(sched, vehicle)
    db.commit()
    return schedules


def get_schedule(db: Session, schedule_id: int) -> VehicleMaintenanceSchedule | None:
    return db.get(VehicleMaintenanceSchedule, schedule_id)


def create_schedule(
    db: Session, vehicle_id: int, payload: MaintenanceScheduleCreate
) -> VehicleMaintenanceSchedule:
    sched = VehicleMaintenanceSchedule(
        **payload.model_dump(), vehicle_id=vehicle_id
    )
    vehicle = db.get(Vehicle, vehicle_id)
    _recompute_schedule(sched, vehicle)
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched


def delete_schedule(db: Session, schedule_id: int) -> bool:
    sched = db.get(VehicleMaintenanceSchedule, schedule_id)
    if sched is None:
        return False
    db.delete(sched)
    db.commit()
    return True


def _recompute_schedule(
    sched: VehicleMaintenanceSchedule, vehicle: Vehicle | None
) -> None:
    """Update next_due_km/date and status based on current mileage."""
    today = date.today()
    current_mileage = vehicle.mileage if vehicle else 0

    if sched.interval_km and sched.last_mileage is not None:
        sched.next_due_km = sched.last_mileage + sched.interval_km
    elif sched.interval_km and sched.next_due_km is None:
        sched.next_due_km = current_mileage + sched.interval_km

    if sched.interval_days and sched.last_date is not None:
        sched.next_due_date = sched.last_date + timedelta(days=sched.interval_days)
    elif sched.interval_days and sched.next_due_date is None:
        sched.next_due_date = today + timedelta(days=sched.interval_days)

    km_over = sched.next_due_km is not None and current_mileage >= sched.next_due_km
    date_over = sched.next_due_date is not None and today >= sched.next_due_date

    if km_over or date_over:
        sched.status = "overdue"
    elif sched.next_due_km is not None and current_mileage >= sched.next_due_km - 500:
        sched.status = "due"
    elif (
        sched.next_due_date is not None
        and today >= sched.next_due_date - timedelta(days=7)
    ):
        sched.status = "due"
    else:
        sched.status = "pending"
