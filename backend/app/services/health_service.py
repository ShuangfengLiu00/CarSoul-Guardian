"""Health snapshot service — create snapshots with items, query history.

The health score can be computed from sub-scores or set directly. When
sub-scores are provided, the overall score is their weighted average.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.health_snapshot import VehicleHealthItem, VehicleHealthSnapshot
from app.models.vehicle import Vehicle
from app.schemas.health_snapshot import HealthSnapshotCreate


# Weighting for overall score when sub-scores are present.
_WEIGHTS: dict[str, float] = {
    "engine_score": 0.25,
    "brake_score": 0.20,
    "tire_score": 0.15,
    "battery_score": 0.15,
    "body_score": 0.10,
    "electronics_score": 0.15,
}


def list_snapshots(
    db: Session, vehicle_id: int, limit: int = 20
) -> list[VehicleHealthSnapshot]:
    stmt = (
        select(VehicleHealthSnapshot)
        .where(VehicleHealthSnapshot.vehicle_id == vehicle_id)
        .order_by(VehicleHealthSnapshot.snapshot_time.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def get_latest_snapshot(db: Session, vehicle_id: int) -> VehicleHealthSnapshot | None:
    stmt = (
        select(VehicleHealthSnapshot)
        .where(VehicleHealthSnapshot.vehicle_id == vehicle_id)
        .order_by(VehicleHealthSnapshot.snapshot_time.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def get_snapshot(db: Session, snapshot_id: int) -> VehicleHealthSnapshot | None:
    return db.get(VehicleHealthSnapshot, snapshot_id)


def get_items(db: Session, snapshot_id: int) -> list[VehicleHealthItem]:
    stmt = select(VehicleHealthItem).where(
        VehicleHealthItem.snapshot_id == snapshot_id
    )
    return list(db.scalars(stmt).all())


def create_snapshot(
    db: Session, vehicle_id: int, payload: HealthSnapshotCreate
) -> VehicleHealthSnapshot:
    """Create a health snapshot with optional sub-items.

    If `health_score` is 0 and sub-scores exist, auto-compute the overall
    score as a weighted average.
    """
    data = payload.model_dump(exclude={"items"})

    # Auto-compute overall score from sub-scores if not explicitly set
    if data.get("health_score", 0) == 0:
        weighted_sum = 0.0
        total_weight = 0.0
        for field, weight in _WEIGHTS.items():
            val = data.get(field)
            if val is not None:
                weighted_sum += val * weight
                total_weight += weight
        if total_weight > 0:
            data["health_score"] = round(weighted_sum / total_weight)

    # Use vehicle mileage if not specified
    if data.get("mileage", 0) == 0:
        vehicle = db.get(Vehicle, vehicle_id)
        if vehicle:
            data["mileage"] = vehicle.mileage

    snapshot = VehicleHealthSnapshot(**data, vehicle_id=vehicle_id)
    db.add(snapshot)
    db.flush()  # get the ID

    # Create health items
    for item_data in payload.items:
        item = VehicleHealthItem(
            **item_data.model_dump(),
            snapshot_id=snapshot.id,
            vehicle_id=vehicle_id,
        )
        db.add(item)

    db.commit()
    db.refresh(snapshot)
    return snapshot


def delete_snapshot(db: Session, snapshot_id: int) -> bool:
    snap = db.get(VehicleHealthSnapshot, snapshot_id)
    if snap is None:
        return False
    db.delete(snap)
    db.commit()
    return True


def compute_health_score(snap: VehicleHealthSnapshot) -> int:
    """Compute an overall score from sub-scores (utility)."""
    weighted_sum = 0.0
    total_weight = 0.0
    for field, weight in _WEIGHTS.items():
        val = getattr(snap, field, None)
        if val is not None:
            weighted_sum += val * weight
            total_weight += weight
    return round(weighted_sum / total_weight) if total_weight > 0 else snap.health_score
