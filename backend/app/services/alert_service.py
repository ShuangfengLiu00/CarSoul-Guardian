"""Alert service — CRUD + lifecycle management (active → acknowledged → resolved)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import VehicleAlert
from app.schemas.alert import AlertCreate, AlertUpdate


def list_alerts(
    db: Session,
    vehicle_id: int,
    status: str | None = None,
    level: str | None = None,
) -> list[VehicleAlert]:
    stmt = select(VehicleAlert).where(VehicleAlert.vehicle_id == vehicle_id)
    if status:
        stmt = stmt.where(VehicleAlert.status == status)
    if level:
        stmt = stmt.where(VehicleAlert.level == level)
    stmt = stmt.order_by(
        VehicleAlert.status.asc(),
        VehicleAlert.triggered_at.desc(),
    )
    return list(db.scalars(stmt).all())


def get_alert(db: Session, alert_id: int) -> VehicleAlert | None:
    return db.get(VehicleAlert, alert_id)


def create_alert(
    db: Session, vehicle_id: int, payload: AlertCreate
) -> VehicleAlert:
    alert = VehicleAlert(**payload.model_dump(), vehicle_id=vehicle_id)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def update_alert(
    db: Session, alert_id: int, payload: AlertUpdate
) -> VehicleAlert | None:
    alert = db.get(VehicleAlert, alert_id)
    if alert is None:
        return None
    if payload.status:
        alert.status = payload.status
        if payload.status == "acknowledged":
            alert.acknowledged_at = datetime.utcnow()
        elif payload.status == "resolved":
            alert.resolved_at = datetime.utcnow()
            if alert.acknowledged_at is None:
                alert.acknowledged_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)
    return alert


def delete_alert(db: Session, alert_id: int) -> bool:
    alert = db.get(VehicleAlert, alert_id)
    if alert is None:
        return False
    db.delete(alert)
    db.commit()
    return True


def count_active(db: Session, vehicle_id: int) -> int:
    stmt = select(VehicleAlert).where(
        VehicleAlert.vehicle_id == vehicle_id,
        VehicleAlert.status == "active",
    )
    return len(list(db.scalars(stmt).all()))
