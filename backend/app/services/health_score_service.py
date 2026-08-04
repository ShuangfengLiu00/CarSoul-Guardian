"""Vehicle Health Score (VHS) service.

Implements the weighted health-score model from the TASK007 spec::

    VHS = 0.30·Engine + 0.25·Battery + 0.15·Chassis
          + 0.15·Driving + 0.15·Maintenance

Grading bands:
    95-100  黄金车况  (golden)
    80-95   优秀      (excellent)
    60-80   一般      (fair)
    <60     风险车辆  (risk)

The score pulls from the latest health snapshot (sub-system scores), the
digital state (real-time health), recent driving behaviour (safety score),
and maintenance records (freshness / completeness).
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.digital_state import VehicleDigitalState
from app.models.driving_behavior import VehicleDrivingBehavior
from app.models.health_snapshot import VehicleHealthSnapshot
from app.models.maintenance import VehicleMaintenanceRecord
from app.models.vehicle import Vehicle
from app.schemas.vehicle_life import (
    HealthScoreBreakdown,
    VehicleHealthScore,
)

# Weights per the spec.
WEIGHTS = {
    "engine": 0.30,
    "battery": 0.25,
    "chassis": 0.15,
    "driving": 0.15,
    "maintenance": 0.15,
}


def _grade(score: float) -> tuple[str, str]:
    if score >= 95:
        return "golden", "黄金车况"
    if score >= 80:
        return "excellent", "优秀"
    if score >= 60:
        return "fair", "一般"
    return "risk", "风险车辆"


def _driving_score(db: Session, vehicle_id: int) -> float:
    """Average safety_score over the last 30 days of driving behaviour."""
    cutoff = date.today() - timedelta(days=30)
    rows = list(
        db.scalars(
            select(VehicleDrivingBehavior.safety_score)
            .where(
                VehicleDrivingBehavior.vehicle_id == vehicle_id,
                VehicleDrivingBehavior.record_date >= cutoff,
                VehicleDrivingBehavior.safety_score.is_not(None),
            )
        ).all()
    )
    if not rows:
        # Fallback: assume decent driving if no data.
        return 85.0
    return float(sum(rows) / len(rows))


def _maintenance_score(db: Session, vehicle_id: int, mileage: int) -> float:
    """Score based on maintenance freshness and completeness.

    Starts at 90 and is penalised for:
    - overdue intervals (no maintenance in a long time / high mileage gap)
    - high cost concentration (many repairs = wear)
    """
    base = 90.0
    records = list(
        db.scalars(
            select(VehicleMaintenanceRecord)
            .where(VehicleMaintenanceRecord.vehicle_id == vehicle_id)
            .order_by(VehicleMaintenanceRecord.maintenance_date.desc())
            .limit(20)
        ).all()
    )

    if not records:
        # No maintenance history at all → assume new vehicle, neutral.
        return base if mileage < 5000 else 55.0

    # Most recent maintenance
    latest = records[0]
    days_since = (date.today() - latest.maintenance_date).days
    km_since = (mileage - (latest.mileage or mileage)) if latest.mileage else 0

    # Penalty for stale maintenance
    if days_since > 365:
        base -= 20
    elif days_since > 180:
        base -= 10
    if km_since > 15000:
        base -= 15
    elif km_since > 10000:
        base -= 8

    # Penalty for many repair-type records (wear indicator)
    repair_count = sum(1 for r in records if r.maintenance_type == "repair")
    if repair_count >= 3:
        base -= 10

    return max(40.0, min(100.0, base))


def compute_health_score(db: Session, vehicle_id: int) -> VehicleHealthScore | None:
    """Compute the full VHS for a vehicle."""
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return None

    # ---- Source sub-scores ----
    # Prefer the latest health snapshot for engine/battery/chassis.
    snap = db.scalar(
        select(VehicleHealthSnapshot)
        .where(VehicleHealthSnapshot.vehicle_id == vehicle_id)
        .order_by(VehicleHealthSnapshot.snapshot_time.desc())
    )
    # Real-time digital state as fallback / supplement.
    state = db.scalar(
        select(VehicleDigitalState).where(
            VehicleDigitalState.vehicle_id == vehicle_id
        )
    )

    def _pick(*candidates):
        for c in candidates:
            if c is not None:
                return float(c)
        return 0.0

    engine = _pick(
        snap.engine_score if snap else None,
        state.engine_health if state else None,
        85.0,
    )
    battery = _pick(
        snap.battery_score if snap else None,
        state.battery_health if state else None,
        85.0,
    )
    # Chassis = mean of brake + tire + body (from snapshot or state)
    brake = _pick(
        snap.brake_score if snap else None,
        state.brake_health if state else None,
        85.0,
    )
    tire = _pick(
        snap.tire_score if snap else None,
        state.tire_health if state else None,
        85.0,
    )
    body = _pick(
        snap.body_score if snap else None,
        state.body_health if state else None,
        90.0,
    )
    chassis = (brake + tire + body) / 3

    driving = _driving_score(db, vehicle_id)
    maintenance = _maintenance_score(db, vehicle_id, vehicle.mileage)

    # ---- Weighted sum ----
    e_c = engine * WEIGHTS["engine"]
    b_c = battery * WEIGHTS["battery"]
    c_c = chassis * WEIGHTS["chassis"]
    d_c = driving * WEIGHTS["driving"]
    m_c = maintenance * WEIGHTS["maintenance"]
    score = round(e_c + b_c + c_c + d_c + m_c, 1)

    grade, grade_label = _grade(score)

    breakdown = HealthScoreBreakdown(
        engine=round(engine, 1),
        battery=round(battery, 1),
        chassis=round(chassis, 1),
        driving=round(driving, 1),
        maintenance=round(maintenance, 1),
        engine_contribution=round(e_c, 2),
        battery_contribution=round(b_c, 2),
        chassis_contribution=round(c_c, 2),
        driving_contribution=round(d_c, 2),
        maintenance_contribution=round(m_c, 2),
    )

    return VehicleHealthScore(
        vehicle_id=vehicle_id,
        score=score,
        grade=grade,
        grade_label=grade_label,
        breakdown=breakdown,
        weights=dict(WEIGHTS),
    )
