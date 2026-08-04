"""Fault log service — vehicle disease history CRUD."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fault_log import VehicleFaultLog
from app.schemas.fault_log import FaultLogCreate, FaultLogUpdate


def list_faults(
    db: Session,
    vehicle_id: int,
    repair_status: str | None = None,
    limit: int = 100,
) -> list[VehicleFaultLog]:
    stmt = (
        select(VehicleFaultLog)
        .where(VehicleFaultLog.vehicle_id == vehicle_id)
        .order_by(VehicleFaultLog.occur_time.desc())
        .limit(limit)
    )
    if repair_status:
        stmt = stmt.where(VehicleFaultLog.repair_status == repair_status)
    return list(db.scalars(stmt).all())


def get_fault(db: Session, fault_id: int) -> VehicleFaultLog | None:
    return db.get(VehicleFaultLog, fault_id)


def create_fault(
    db: Session, vehicle_id: int, payload: FaultLogCreate
) -> VehicleFaultLog:
    data = payload.model_dump()
    # Let DB default occur_time if not provided
    if data.get("occur_time") is None:
        data.pop("occur_time")
    fault = VehicleFaultLog(vehicle_id=vehicle_id, **data)
    db.add(fault)
    db.commit()
    db.refresh(fault)
    return fault


def update_fault(
    db: Session, fault_id: int, payload: FaultLogUpdate
) -> VehicleFaultLog | None:
    fault = db.get(VehicleFaultLog, fault_id)
    if fault is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    for key, val in data.items():
        setattr(fault, key, val)
    # Auto-set resolved_time when marking resolved
    if data.get("repair_status") == "resolved" and not fault.resolved_time:
        fault.resolved_time = datetime.utcnow()
    db.commit()
    db.refresh(fault)
    return fault


def delete_fault(db: Session, fault_id: int) -> bool:
    fault = db.get(VehicleFaultLog, fault_id)
    if fault is None:
        return False
    db.delete(fault)
    db.commit()
    return True


def count_faults(db: Session, vehicle_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(VehicleFaultLog)
        .where(VehicleFaultLog.vehicle_id == vehicle_id)
    ) or 0


def count_active_faults(db: Session, vehicle_id: int) -> int:
    return db.scalar(
        select(func.count())
        .select_from(VehicleFaultLog)
        .where(
            VehicleFaultLog.vehicle_id == vehicle_id,
            VehicleFaultLog.repair_status != "resolved",
        )
    ) or 0
