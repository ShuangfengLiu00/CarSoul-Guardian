"""Digital twin service — one twin per vehicle."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.digital_twin import VehicleDigitalTwin
from app.models.vehicle import Vehicle
from app.schemas.digital_twin import DigitalTwinCreate, DigitalTwinUpdate


def get_twin(db: Session, vehicle_id: int) -> VehicleDigitalTwin | None:
    return db.scalar(
        select(VehicleDigitalTwin).where(
            VehicleDigitalTwin.vehicle_id == vehicle_id
        )
    )


def create_twin(
    db: Session, vehicle_id: int, payload: DigitalTwinCreate
) -> VehicleDigitalTwin:
    # Ensure vehicle exists
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise ValueError(f"Vehicle {vehicle_id} not found")

    # Check if twin already exists
    existing = get_twin(db, vehicle_id)
    if existing:
        raise ValueError(f"Digital twin already exists for vehicle {vehicle_id}")

    twin = VehicleDigitalTwin(**payload.model_dump(), vehicle_id=vehicle_id)
    twin.sync_status = "synced"
    twin.last_sync_at = datetime.utcnow()
    db.add(twin)

    # Update vehicle's twin reference
    vehicle.twin_model_id = twin.model_url or twin.model_version
    vehicle.twin_last_sync = twin.last_sync_at

    db.commit()
    db.refresh(twin)
    return twin


def update_twin(
    db: Session, vehicle_id: int, payload: DigitalTwinUpdate
) -> VehicleDigitalTwin | None:
    twin = get_twin(db, vehicle_id)
    if twin is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    for key, val in data.items():
        setattr(twin, key, val)
    twin.last_sync_at = datetime.utcnow()
    twin.sync_status = "synced"

    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle:
        vehicle.twin_last_sync = twin.last_sync_at

    db.commit()
    db.refresh(twin)
    return twin


def sync_telemetry(
    db: Session, vehicle_id: int, telemetry: dict
) -> VehicleDigitalTwin | None:
    """Push a real-time telemetry update to the twin."""
    twin = get_twin(db, vehicle_id)
    if twin is None:
        return None
    twin.telemetry = telemetry
    twin.last_sync_at = datetime.utcnow()
    twin.sync_status = "synced"
    db.commit()
    db.refresh(twin)
    return twin


def delete_twin(db: Session, vehicle_id: int) -> bool:
    twin = get_twin(db, vehicle_id)
    if twin is None:
        return False
    db.delete(twin)
    db.commit()
    return True
