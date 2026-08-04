"""Ownership record service — transfer history."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ownership_record import VehicleOwnershipRecord
from app.schemas.ownership_record import OwnershipRecordCreate


def list_records(
    db: Session, vehicle_id: int
) -> list[VehicleOwnershipRecord]:
    stmt = (
        select(VehicleOwnershipRecord)
        .where(VehicleOwnershipRecord.vehicle_id == vehicle_id)
        .order_by(VehicleOwnershipRecord.start_date.asc())
    )
    return list(db.scalars(stmt).all())


def get_record(db: Session, record_id: int) -> VehicleOwnershipRecord | None:
    return db.get(VehicleOwnershipRecord, record_id)


def create_record(
    db: Session, vehicle_id: int, payload: OwnershipRecordCreate
) -> VehicleOwnershipRecord:
    # Close any existing open ownership for this vehicle
    existing = list(
        db.scalars(
            select(VehicleOwnershipRecord).where(
                VehicleOwnershipRecord.vehicle_id == vehicle_id,
                VehicleOwnershipRecord.end_date.is_(None),
            )
        ).all()
    )
    for rec in existing:
        rec.end_date = payload.start_date

    record = VehicleOwnershipRecord(
        **payload.model_dump(), vehicle_id=vehicle_id
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record_id: int) -> bool:
    record = db.get(VehicleOwnershipRecord, record_id)
    if record is None:
        return False
    db.delete(record)
    db.commit()
    return True
