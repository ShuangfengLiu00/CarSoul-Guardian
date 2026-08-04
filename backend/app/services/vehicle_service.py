"""Vehicle service — CRUD + digital-life archive aggregation (TASK007).

Provides list/get/create/update/delete for vehicles, plus the key
`get_archive()` method that assembles the complete digital-life profile
for a single vehicle (lifecycle timeline, health, maintenance, driving
behaviour, alerts, ownership, digital twin).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.alert import VehicleAlert
from app.models.digital_twin import VehicleDigitalTwin
from app.models.driving_behavior import VehicleDrivingBehavior
from app.models.health_snapshot import VehicleHealthItem, VehicleHealthSnapshot
from app.models.lifecycle_event import VehicleLifecycleEvent
from app.models.maintenance import (
    VehicleMaintenanceRecord,
    VehicleMaintenanceSchedule,
)
from app.models.ownership_record import VehicleOwnershipRecord
from app.models.vehicle import Vehicle
from app.schemas.vehicle import (
    VehicleArchiveOut,
    VehicleCreate,
    VehicleUpdate,
)


# ---------------------------------------------------------------------------
# Vehicle CRUD
# ---------------------------------------------------------------------------

def list_vehicles(db: Session) -> list[Vehicle]:
    stmt = select(Vehicle).order_by(Vehicle.id.asc())
    return list(db.scalars(stmt).all())


def get_vehicle(db: Session, vehicle_id: int) -> Vehicle | None:
    return db.get(Vehicle, vehicle_id)


def get_vehicle_by_vin(db: Session, vin: str) -> Vehicle | None:
    return db.scalar(select(Vehicle).where(Vehicle.vin == vin))


def create_vehicle(
    db: Session, payload: VehicleCreate, owner_id: int | None = None
) -> Vehicle:
    vehicle = Vehicle(**payload.model_dump(), owner_id=owner_id)
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def update_vehicle(
    db: Session, vehicle_id: int, payload: VehicleUpdate
) -> Vehicle | None:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    for key, val in data.items():
        setattr(vehicle, key, val)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def delete_vehicle(db: Session, vehicle_id: int) -> bool:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return False
    db.delete(vehicle)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Archive aggregation
# ---------------------------------------------------------------------------

def get_archive(db: Session, vehicle_id: int) -> VehicleArchiveOut | None:
    """Assemble the complete digital-life archive for a vehicle."""
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return None

    # ---- Lifecycle events (timeline) ----
    events = list(
        db.scalars(
            select(VehicleLifecycleEvent)
            .where(VehicleLifecycleEvent.vehicle_id == vehicle_id)
            .order_by(VehicleLifecycleEvent.event_date.desc())
        ).all()
    )

    # ---- Health snapshots (latest + history) ----
    from app.schemas.health_snapshot import HealthSnapshotOut

    snapshots = list(
        db.scalars(
            select(VehicleHealthSnapshot)
            .where(VehicleHealthSnapshot.vehicle_id == vehicle_id)
            .order_by(VehicleHealthSnapshot.snapshot_time.desc())
        ).all()
    )

    # Load health items for each snapshot and build Pydantic objects
    items_by_snap: dict[int, list[VehicleHealthItem]] = {}
    if snapshots:
        snap_ids = [s.id for s in snapshots[:20]]
        all_items = list(
            db.scalars(
                select(VehicleHealthItem).where(
                    VehicleHealthItem.snapshot_id.in_(snap_ids)
                )
            ).all()
        )
        for item in all_items:
            items_by_snap.setdefault(item.snapshot_id, []).append(item)

    def _snap_to_out(snap: VehicleHealthSnapshot) -> HealthSnapshotOut:
        snap_items = items_by_snap.get(snap.id, [])
        return HealthSnapshotOut(
            id=snap.id,
            vehicle_id=snap.vehicle_id,
            health_score=snap.health_score,
            mileage=snap.mileage,
            engine_score=snap.engine_score,
            brake_score=snap.brake_score,
            tire_score=snap.tire_score,
            battery_score=snap.battery_score,
            body_score=snap.body_score,
            electronics_score=snap.electronics_score,
            summary=snap.summary,
            source=snap.source,
            snapshot_time=snap.snapshot_time,
            items=snap_items,
        )

    latest_health_out = _snap_to_out(snapshots[0]) if snapshots else None
    health_history_out = [_snap_to_out(s) for s in snapshots[:20]]

    # ---- Maintenance records ----
    records = list(
        db.scalars(
            select(VehicleMaintenanceRecord)
            .where(VehicleMaintenanceRecord.vehicle_id == vehicle_id)
            .order_by(VehicleMaintenanceRecord.maintenance_date.desc())
        ).all()
    )

    # ---- Maintenance schedules (recompute status) ----
    schedules = list(
        db.scalars(
            select(VehicleMaintenanceSchedule)
            .where(VehicleMaintenanceSchedule.vehicle_id == vehicle_id)
            .order_by(VehicleMaintenanceSchedule.priority.desc())
        ).all()
    )
    next_maintenance_items: list[dict[str, Any]] = []
    for sched in schedules:
        _recompute_schedule_status(sched, vehicle.mileage)
        if sched.status in ("due", "overdue"):
            next_maintenance_items.append({
                "item_name": sched.item_name,
                "category": sched.category,
                "priority": sched.priority,
                "status": sched.status,
                "next_due_km": sched.next_due_km,
                "next_due_date": sched.next_due_date.isoformat()
                if sched.next_due_date
                else None,
            })
    db.commit()

    # ---- Driving behaviour (recent 30 days) ----
    cutoff = date.today() - timedelta(days=30)
    behaviors = list(
        db.scalars(
            select(VehicleDrivingBehavior)
            .where(
                VehicleDrivingBehavior.vehicle_id == vehicle_id,
                VehicleDrivingBehavior.record_date >= cutoff,
            )
            .order_by(VehicleDrivingBehavior.record_date.desc())
        ).all()
    )

    # ---- Alerts (active first) ----
    alerts = list(
        db.scalars(
            select(VehicleAlert)
            .where(VehicleAlert.vehicle_id == vehicle_id)
            .order_by(
                VehicleAlert.status.asc(),
                VehicleAlert.triggered_at.desc(),
            )
        ).all()
    )

    # ---- Ownership history ----
    ownership = list(
        db.scalars(
            select(VehicleOwnershipRecord)
            .where(VehicleOwnershipRecord.vehicle_id == vehicle_id)
            .order_by(VehicleOwnershipRecord.start_date.asc())
        ).all()
    )

    # ---- Digital twin ----
    twin = db.scalar(
        select(VehicleDigitalTwin).where(
            VehicleDigitalTwin.vehicle_id == vehicle_id
        )
    )

    # ---- Computed summary ----
    active_alerts = [a for a in alerts if a.status == "active"]
    total_cost = sum(r.cost or 0 for r in records)

    return VehicleArchiveOut(
        vehicle=vehicle,
        lifecycle_events=events,
        latest_health=latest_health_out,
        health_history=health_history_out,
        maintenance_records=records,
        maintenance_schedules=schedules,
        driving_behaviors=behaviors,
        alerts=alerts,
        ownership_history=ownership,
        digital_twin=twin,
        health_score=latest_health_out.health_score if latest_health_out else None,
        active_alert_count=len(active_alerts),
        total_maintenance_cost=total_cost,
        next_maintenance_items=next_maintenance_items,
    )


# ---------------------------------------------------------------------------
# Schedule status computation
# ---------------------------------------------------------------------------

def _recompute_schedule_status(
    sched: VehicleMaintenanceSchedule, current_mileage: int
) -> None:
    """Update next_due_km/date and status on a schedule row."""
    today = date.today()

    # Compute next due km
    if sched.interval_km and sched.last_mileage is not None:
        sched.next_due_km = sched.last_mileage + sched.interval_km
    elif sched.interval_km and sched.next_due_km is None:
        sched.next_due_km = current_mileage + sched.interval_km

    # Compute next due date
    if sched.interval_days and sched.last_date is not None:
        sched.next_due_date = sched.last_date + timedelta(days=sched.interval_days)
    elif sched.interval_days and sched.next_due_date is None:
        sched.next_due_date = today + timedelta(days=sched.interval_days)

    # Determine status
    km_over = (
        sched.next_due_km is not None and current_mileage >= sched.next_due_km
    )
    date_over = (
        sched.next_due_date is not None and today >= sched.next_due_date
    )
    if km_over or date_over:
        sched.status = "overdue"
    elif sched.next_due_km is not None and current_mileage >= sched.next_due_km - 500:
        sched.status = "due"
    elif sched.next_due_date is not None and today >= sched.next_due_date - timedelta(days=7):
        sched.status = "due"
    else:
        sched.status = "pending"
