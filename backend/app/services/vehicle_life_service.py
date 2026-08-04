"""Vehicle digital-life record service (TASK007 flagship read model).

Assembles the ``VehicleLifeRecord`` — the narrative "digital life" view that
powers the *Vehicle Digital Life Home* page. Pulls from every digital-life
table: profile, digital state, health snapshots, lifecycle events,
maintenance, trips, faults, driving behaviour, and risk predictions.

Also reserved AI-extension hooks for TASK008 (AI vehicle doctor +
personality).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.digital_state import VehicleDigitalState
from app.models.driving_behavior import VehicleDrivingBehavior
from app.models.fault_log import VehicleFaultLog
from app.models.lifecycle_event import VehicleLifecycleEvent
from app.models.maintenance import VehicleMaintenanceRecord, VehicleMaintenanceSchedule
from app.models.risk_prediction import RiskPrediction
from app.models.trip import VehicleTrip
from app.models.vehicle import Vehicle
from app.schemas.vehicle_life import (
    LifeEventItem,
    PredictionItem,
    VehicleHealthScore,
    VehicleIdentity,
    VehicleLifeRecord,
)
from app.services import health_score_service

# Average design lifespan (years) by energy type — used for predictions.
_DESIGN_LIFESPAN = {
    "electric": 12.0,
    "hybrid": 12.0,
    "plug_in_hybrid": 12.0,
    "gasoline": 15.0,
    "diesel": 15.0,
}

# Mileage at which a vehicle is considered end-of-life (km).
_EOL_MILEAGE = 300_000


def _digital_identity(vehicle: Vehicle) -> str:
    """Build the human-readable digital identity code VX-YYYY-NNNNN."""
    year = vehicle.year or vehicle.purchase_date.year if vehicle.purchase_date else datetime.utcnow().year
    return f"VX-{year}-{vehicle.id:05d}"


def _age_years(vehicle: Vehicle) -> float:
    ref = vehicle.purchase_date or vehicle.registration_date
    if ref is None:
        return 0.0
    delta = date.today() - ref
    return round(delta.days / 365.25, 1)


def _age_label(years: float) -> str:
    if years < 0.1:
        return "新车"
    if years < 1:
        months = int(years * 12)
        return f"{months}个月"
    y = int(years)
    m = int((years - y) * 12)
    return f"{y}年{m}个月" if m else f"{y}年"


def _status_label(status: str) -> str:
    return {
        "GOOD": "健康",
        "WARNING": "注意",
        "DANGER": "危险",
        "END_OF_LIFE": "报废",
    }.get(status, status)


def _predicted_lifespan(vehicle: Vehicle, health_score: float | None) -> tuple[float | None, str | None]:
    """Estimate remaining lifespan based on age, mileage, and health."""
    design = _DESIGN_LIFESPAN.get(vehicle.fuel_type, 14.0)
    age = _age_years(vehicle)

    # Mileage-based remaining
    if vehicle.mileage >= _EOL_MILEAGE:
        return 0.0, "已达设计寿命"
    mileage_remaining_years = (_EOL_MILEAGE - vehicle.mileage) / max(1, vehicle.mileage / max(0.1, age)) if age > 0.5 else None

    # Health-adjusted: lower health shortens remaining life.
    health_factor = 1.0
    if health_score is not None:
        if health_score >= 90:
            health_factor = 1.05
        elif health_score >= 75:
            health_factor = 1.0
        elif health_score >= 60:
            health_factor = 0.8
        else:
            health_factor = 0.55

    remaining_age = max(0.0, design - age)
    if mileage_remaining_years is not None:
        remaining = min(remaining_age, mileage_remaining_years) * health_factor
    else:
        remaining = remaining_age * health_factor

    remaining = max(0.0, round(remaining, 1))
    total = round(age + remaining, 1)
    label = f"预计总寿命 {total} 年，剩余约 {remaining} 年"
    return remaining, label


def _build_life_events(
    db: Session, vehicle_id: int
) -> list[LifeEventItem]:
    """Merge lifecycle events + maintenance records into a unified timeline."""
    events: list[LifeEventItem] = []

    for ev in db.scalars(
        select(VehicleLifecycleEvent)
        .where(VehicleLifecycleEvent.vehicle_id == vehicle_id)
        .order_by(VehicleLifecycleEvent.event_date.desc())
        .limit(50)
    ).all():
        events.append(LifeEventItem(
            date=ev.event_date,
            event_type=ev.event_type,
            title=ev.title,
            description=ev.description,
            mileage=ev.mileage,
            cost=ev.cost,
        ))

    for rec in db.scalars(
        select(VehicleMaintenanceRecord)
        .where(VehicleMaintenanceRecord.vehicle_id == vehicle_id)
        .order_by(VehicleMaintenanceRecord.maintenance_date.desc())
        .limit(30)
    ).all():
        events.append(LifeEventItem(
            date=rec.maintenance_date,
            event_type="maintenance",
            title=rec.title,
            description=rec.description,
            mileage=rec.mileage,
            cost=rec.cost,
        ))

    for flt in db.scalars(
        select(VehicleFaultLog)
        .where(VehicleFaultLog.vehicle_id == vehicle_id)
        .order_by(VehicleFaultLog.occur_time.desc())
        .limit(20)
    ).all():
        events.append(LifeEventItem(
            date=flt.occur_time,
            event_type="fault",
            title=f"故障 {flt.fault_code}",
            description=flt.description,
            mileage=flt.mileage,
        ))

    # Sort by date descending and dedupe by title+date.
    def _sort_key(e: LifeEventItem):
        d = e.date
        # Normalise datetime -> date so date and datetime are comparable.
        return d.date() if isinstance(d, datetime) else d

    events.sort(key=_sort_key, reverse=True)
    return events[:40]


def _build_predictions(
    db: Session, vehicle_id: int
) -> list[PredictionItem]:
    """Build AI-style predictions from risk predictions + overdue schedules."""
    predictions: list[PredictionItem] = []

    # From risk predictions (forward-looking)
    for rp in db.scalars(
        select(RiskPrediction)
        .where(
            RiskPrediction.vehicle_id == vehicle_id,
            RiskPrediction.status.in_(["open", "acknowledged"]),
        )
        .order_by(RiskPrediction.created_at.desc())
        .limit(10)
    ).all():
        risk_map = {"info": "low", "warning": "medium", "urgent": "high"}
        predictions.append(PredictionItem(
            component=rp.primary_type or "整车",
            current_health=None,
            predicted_failure_date=(
                datetime.utcnow() + timedelta(hours=rp.predicted_eta_hours or 720)
            ).date() if rp.predicted_eta_hours else None,
            risk_level=risk_map.get(rp.predicted_level, "medium"),
            reason=rp.root_cause or rp.explanation or "系统检测到异常趋势",
            suggestion=rp.explanation,
        ))

    # From overdue / due maintenance schedules
    for sched in db.scalars(
        select(VehicleMaintenanceSchedule)
        .where(
            VehicleMaintenanceSchedule.vehicle_id == vehicle_id,
            VehicleMaintenanceSchedule.status.in_(["due", "overdue"]),
        )
        .order_by(VehicleMaintenanceSchedule.priority.desc())
        .limit(10)
    ).all():
        risk_map = {"high": "high", "medium": "medium", "low": "low"}
        km_hint = f"（下次: {sched.next_due_km} km）" if sched.next_due_km else ""
        predictions.append(PredictionItem(
            component=sched.category,
            current_health=None,
            predicted_failure_date=sched.next_due_date,
            risk_level=risk_map.get(sched.priority, "medium"),
            reason=f"{sched.item_name} 即将到期{km_hint}",
            suggestion=f"安排 {sched.item_name}",
        ))

    # From fault logs (active faults)
    for flt in db.scalars(
        select(VehicleFaultLog)
        .where(
            VehicleFaultLog.vehicle_id == vehicle_id,
            VehicleFaultLog.repair_status != "resolved",
        )
        .order_by(VehicleFaultLog.fault_level.desc())
        .limit(5)
    ).all():
        level_map = {"low": "low", "medium": "medium", "high": "high", "critical": "high"}
        predictions.append(PredictionItem(
            component=flt.system or "unknown",
            current_health=None,
            predicted_failure_date=None,
            risk_level=level_map.get(flt.fault_level, "medium"),
            reason=f"存在未解决故障 {flt.fault_code}: {flt.description or ''}",
            suggestion="尽快检修",
        ))

    return predictions[:10]


def _build_ai_suggestions(
    vehicle: Vehicle,
    health_score: VehicleHealthScore | None,
    predictions: list[PredictionItem],
) -> list[str]:
    """Generate human-readable AI suggestions (rule-based, TASK008 will upgrade)."""
    suggestions: list[str] = []

    if health_score:
        b = health_score.breakdown
        if b.chassis < 75:
            suggestions.append(f"底盘(制动/轮胎/车身)评分 {b.chassis:.0f}，建议未来 5000 公里内检查刹车片与轮胎。")
        if b.battery < 75:
            suggestions.append(f"电池/电力系统评分 {b.battery:.0f}，建议进行电池健康检测。")
        if b.engine < 75:
            suggestions.append(f"发动机评分 {b.engine:.0f}，建议安排全面检查。")
        if b.maintenance < 70:
            suggestions.append("保养记录不完整，建议按周期进行常规保养。")
        if b.driving < 75:
            suggestions.append(f"驾驶习惯评分 {b.driving:.0f}，建议减少急加速急刹车。")
        if not suggestions and health_score.score >= 85:
            suggestions.append("车辆整体状况优秀，保持当前保养节奏即可。")

    for p in predictions[:3]:
        if p.risk_level == "high":
            suggestions.append(f"【高风险】{p.reason} — {p.suggestion or '请尽快处理'}")

    if not suggestions:
        suggestions.append("暂无紧急建议，车辆运行正常。")

    return suggestions


def get_life_record(db: Session, vehicle_id: int) -> VehicleLifeRecord | None:
    """Assemble the complete digital-life record for a vehicle."""
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return None

    # ---- Health score (VHS) ----
    hs = health_score_service.compute_health_score(db, vehicle_id)

    # ---- Digital state ----
    state = db.scalar(
        select(VehicleDigitalState).where(
            VehicleDigitalState.vehicle_id == vehicle_id
        )
    )

    # ---- Age / lifespan ----
    age = _age_years(vehicle)
    remaining, lifespan_label = _predicted_lifespan(
        vehicle, hs.score if hs else None
    )

    # ---- Counts ----
    trip_count = db.scalar(
        select(func.count()).select_from(VehicleTrip)
        .where(VehicleTrip.vehicle_id == vehicle_id)
    ) or 0
    total_cost = db.scalar(
        select(func.coalesce(func.sum(VehicleMaintenanceRecord.cost), 0))
        .where(VehicleMaintenanceRecord.vehicle_id == vehicle_id)
    ) or 0.0
    fault_count = db.scalar(
        select(func.count()).select_from(VehicleFaultLog)
        .where(VehicleFaultLog.vehicle_id == vehicle_id)
    ) or 0
    active_faults = db.scalar(
        select(func.count()).select_from(VehicleFaultLog)
        .where(
            VehicleFaultLog.vehicle_id == vehicle_id,
            VehicleFaultLog.repair_status != "resolved",
        )
    ) or 0

    # ---- Timeline + predictions + suggestions ----
    life_events = _build_life_events(db, vehicle_id)
    predictions = _build_predictions(db, vehicle_id)
    suggestions = _build_ai_suggestions(vehicle, hs, predictions)

    # ---- Identity ----
    identity = VehicleIdentity(
        vehicle_id=vehicle.id,
        digital_identity=_digital_identity(vehicle),
        name=vehicle.nickname or f"{vehicle.brand} {vehicle.model}",
        brand=vehicle.brand,
        model=vehicle.model,
        year=vehicle.year,
        vin=vehicle.vin,
        energy_type=vehicle.fuel_type,
        color=vehicle.color,
        nickname=vehicle.nickname,
        avatar_url=vehicle.avatar_url,
    )

    status = state.status if state else "GOOD"

    return VehicleLifeRecord(
        identity=identity,
        health_score=round(hs.score) if hs else None,
        health_grade=hs.grade if hs else None,
        health_grade_label=hs.grade_label if hs else None,
        status=status,
        status_label=_status_label(status),
        age_years=age,
        age_label=_age_label(age),
        mileage=vehicle.mileage,
        mileage_label=f"{vehicle.mileage:,} km",
        predicted_lifespan_years=remaining,
        predicted_remaining_years=remaining,
        predicted_lifespan_label=lifespan_label,
        today_temperature=state.temperature if state else None,
        today_fuel_level=state.fuel_level if state else None,
        today_location=state.location if state else None,
        engine_health=state.engine_health if state else None,
        battery_health=state.battery_health if state else None,
        brake_health=state.brake_health if state else None,
        tire_health=state.tire_health if state else None,
        health_breakdown=hs.breakdown if hs else None,
        life_events=life_events,
        predictions=predictions,
        ai_suggestions=suggestions,
        total_trips=trip_count,
        total_maintenance_cost=round(float(total_cost), 2),
        fault_count=fault_count,
        active_fault_count=active_faults,
        ai_doctor_enabled=False,
        personality=None,
    )
