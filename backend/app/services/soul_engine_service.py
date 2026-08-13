"""Soul Engine service — Vehicle Digital Life Engine core (TASK007-V2).

Implements the Vehicle Soul Score (VSS) model, digital identity generation,
life-stage determination, memory management, and the Soul Profile aggregation.

VSS Formula:
    VSS = Health ×40% + Memory ×15% + Maintenance ×15% + Driving ×15% + Prediction ×15%

Grades:
    95-100  →  legendary (传奇状态)
    80-95   →  excellent (优秀状态)
    60-80   →  normal    (正常状态)
    <60     →  risk      (风险状态)
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.digital_life import (
    DriverProfile,
    VehicleHealthMetrics,
    VehicleIdentity,
    VehicleLifeEvent,
    VehicleLifeState,
    VehicleMemory,
    VehiclePrediction,
    VehicleSensorStream,
    VehicleSoulScoreHistory,
)
from app.models.maintenance import VehicleMaintenanceRecord
from app.models.vehicle import Vehicle
from app.schemas.digital_life import (
    CreateDigitalLifeResponse,
    DriverProfileOut,
    SoulScoreBreakdown,
    SoulProfile,
    VehicleHealthMetricsCreate,
    VehicleHealthMetricsOut,
    VehicleIdentityCreate,
    VehicleIdentityOut,
    VehicleLifeEventCreate,
    VehicleLifeEventOut,
    VehicleMemoryCreate,
    VehicleMemoryOut,
    VehiclePredictionCreate,
    VehiclePredictionOut,
    VehicleSoulScore,
    VehicleSoulScoreHistoryOut,
)

# ===========================================================================
# Constants
# ===========================================================================

_VSS_WEIGHTS = {
    "health": 0.40,
    "memory": 0.15,
    "maintenance": 0.15,
    "driving": 0.15,
    "prediction": 0.15,
}

_LIFE_STAGE_LABELS = {
    "NEW": "新生期",
    "GROWTH": "成长期",
    "MATURE": "成熟期",
    "AGING": "老化期",
    "RETIRE": "退役期",
}

_SOUL_GRADE_LABELS = {
    "legendary": "传奇状态",
    "excellent": "优秀状态",
    "normal": "正常状态",
    "risk": "风险状态",
}

_DRIVER_STYLE_LABELS = {
    "conservative": "稳健型",
    "balanced": "均衡型",
    "aggressive": "激进型",
    "eco": "节能型",
    "sporty": "运动型",
}


def _soul_grade(score: float) -> tuple[str, str]:
    """Return (grade, label) for a soul score."""
    if score >= 95:
        return "legendary", _SOUL_GRADE_LABELS["legendary"]
    if score >= 80:
        return "excellent", _SOUL_GRADE_LABELS["excellent"]
    if score >= 60:
        return "normal", _SOUL_GRADE_LABELS["normal"]
    return "risk", _SOUL_GRADE_LABELS["risk"]


def _life_stage_for(age_days: int, mileage: int) -> str:
    """Determine life stage from age and mileage."""
    if age_days < 90 or mileage < 3000:
        return "NEW"
    if age_days < 365 or mileage < 20000:
        return "GROWTH"
    if age_days < 1825 or mileage < 100000:
        return "MATURE"
    if age_days < 3650 or mileage < 200000:
        return "AGING"
    return "RETIRE"


# ===========================================================================
# 1. Digital Identity
# ===========================================================================

def create_digital_identity(
    db: Session, vehicle: Vehicle, payload: VehicleIdentityCreate | None = None
) -> VehicleIdentity:
    """Create a digital identity (soul) for a vehicle."""
    now = datetime.utcnow()
    year = vehicle.year or now.year
    # Generate soul UUID: CSG-YYYY-NNNNN
    existing_count = db.scalar(
        select(func.count()).select_from(VehicleIdentity)
    ) or 0
    seq = existing_count + 1
    soul_uuid = f"CSG-{year}-{seq:05d}"

    identity = VehicleIdentity(
        vehicle_id=vehicle.id,
        vehicle_uuid=soul_uuid,
        vin=vehicle.vin,
        brand=vehicle.brand,
        model=vehicle.model,
        production_year=vehicle.year,
        energy_type=vehicle.fuel_type,
        vehicle_class=_infer_vehicle_class(vehicle),
        owner_id=vehicle.owner_id,
        birth_time=vehicle.purchase_date or now,
        nickname=vehicle.nickname,
    )
    db.add(identity)
    db.flush()

    # Also create the life state record
    age_days = (date.today() - (vehicle.purchase_date or date.today())).days if vehicle.purchase_date else 0
    life_state = VehicleLifeState(
        vehicle_id=vehicle.id,
        life_stage=_life_stage_for(age_days, vehicle.mileage),
        mileage=vehicle.mileage,
        vehicle_age_days=age_days,
        health_score=90.0,
        energy_health=90.0,
        mechanical_health=90.0,
        software_health=95.0,
        soul_score=None,  # Will be computed later
    )
    db.add(life_state)
    db.flush()

    return identity


def _infer_vehicle_class(vehicle: Vehicle) -> str:
    """Infer vehicle class from model name."""
    model_lower = (vehicle.model or "").lower()
    if any(k in model_lower for k in ["y", "model y", "es", "rx", "q5", "glc", "x3"]):
        return "SUV"
    if any(k in model_lower for k in ["model 3", "s", "汉", "a4", "3系", "c级"]):
        return "sedan"
    return "sedan"


def get_identity(db: Session, vehicle_id: int) -> VehicleIdentity | None:
    return db.scalar(
        select(VehicleIdentity).where(VehicleIdentity.vehicle_id == vehicle_id)
    )


def get_or_create_identity(db: Session, vehicle_id: int) -> VehicleIdentity:
    """Get or create the digital identity for a vehicle."""
    identity = get_identity(db, vehicle_id)
    if identity is not None:
        return identity
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise ValueError(f"Vehicle {vehicle_id} not found")
    return create_digital_identity(db, vehicle)


# ===========================================================================
# 2. Vehicle Soul Score (VSS)
# ===========================================================================

def _compute_health_score(db: Session, vehicle_id: int) -> float:
    """车辆健康分统一口径：复用 Guardian 权威 VHS（health_score_service）。

    收敛 P1（健康分三定义矛盾）：此前数字生命的 health 子项用另一套
    ``VehicleHealthMetrics`` 均值公式，与首页/档案的 VHS(84.1) 各算各的，
    导致「数字生命页 93 / 首页 84」的口径漂移。现在统一取 VHS，
    digital-twin 的 health 维度、life_state.health_score、profile.health_score
    全部等于 VHS，与车辆健康分单一口径对齐。

    兜底：VHS 极端情况下算不出（车辆不存在等）时，回落到原指标均值逻辑，
    避免引入新失败点。
    """
    from app.services.health_score_service import compute_health_score

    vhs = compute_health_score(db, vehicle_id)
    if vhs is not None:
        return float(vhs.score)

    # ---- 兜底：原 VehicleHealthMetrics 均值逻辑（仅 VHS 不可得时） ----
    latest = db.scalars(
        select(VehicleHealthMetrics)
        .where(VehicleHealthMetrics.vehicle_id == vehicle_id)
        .order_by(VehicleHealthMetrics.record_time.desc())
        .limit(10)
    ).all()
    if not latest:
        from app.models.digital_state import VehicleDigitalState
        state = db.scalar(
            select(VehicleDigitalState).where(
                VehicleDigitalState.vehicle_id == vehicle_id
            )
        )
        if state and state.overall_score:
            return float(state.overall_score)
        return 85.0

    scores = [m.health_score for m in latest if m.health_score is not None]
    return sum(scores) / len(scores) if scores else 85.0


def _compute_memory_score(db: Session, vehicle_id: int) -> float:
    """Compute memory sub-score (0-100) from memory richness."""
    count = db.scalar(
        select(func.count()).select_from(VehicleMemory)
        .where(VehicleMemory.vehicle_id == vehicle_id)
    ) or 0
    # 0 memories → 50, 50 memories → 75, 100+ → 95
    return min(95.0, 50.0 + count * 0.45)


def _compute_maintenance_score(db: Session, vehicle_id: int) -> float:
    """Compute maintenance sub-score (0-100) from maintenance quality."""
    # Check if maintenance is up to date
    from app.models.maintenance import VehicleMaintenanceSchedule

    total_schedules = db.scalar(
        select(func.count()).select_from(VehicleMaintenanceSchedule)
        .where(VehicleMaintenanceSchedule.vehicle_id == vehicle_id)
    ) or 0
    overdue = db.scalar(
        select(func.count()).select_from(VehicleMaintenanceSchedule)
        .where(
            VehicleMaintenanceSchedule.vehicle_id == vehicle_id,
            VehicleMaintenanceSchedule.status == "overdue",
        )
    ) or 0
    due = db.scalar(
        select(func.count()).select_from(VehicleMaintenanceSchedule)
        .where(
            VehicleMaintenanceSchedule.vehicle_id == vehicle_id,
            VehicleMaintenanceSchedule.status == "due",
        )
    ) or 0

    if total_schedules == 0:
        return 70.0

    completed_ratio = 1.0 - (overdue + due * 0.5) / max(1, total_schedules)
    return round(max(40.0, min(100.0, completed_ratio * 100)), 1)


def _compute_driving_score(db: Session, vehicle_id: int) -> float:
    """Compute driving sub-score (0-100) from driver profile + behavior."""
    profile = db.scalar(
        select(DriverProfile).where(DriverProfile.vehicle_id == vehicle_id)
    )
    if profile and profile.eco_score is not None:
        # Blend eco + comfort - aggressive
        eco = profile.eco_score or 80
        comfort = profile.comfort_score or 80
        aggressive = profile.aggressive_score or 30
        return round((eco * 0.4 + comfort * 0.4 + (100 - aggressive) * 0.2), 1)

    # Fallback to driving behavior
    from app.models.driving_behavior import VehicleDrivingBehavior
    behaviors = db.scalars(
        select(VehicleDrivingBehavior)
        .where(VehicleDrivingBehavior.vehicle_id == vehicle_id)
        .order_by(VehicleDrivingBehavior.record_date.desc())
        .limit(30)
    ).all()
    if not behaviors:
        return 75.0
    safety_scores = [b.safety_score for b in behaviors if b.safety_score is not None]
    eco_scores = [b.eco_score for b in behaviors if b.eco_score is not None]
    avg_safety = sum(safety_scores) / len(safety_scores) if safety_scores else 75
    avg_eco = sum(eco_scores) / len(eco_scores) if eco_scores else 75
    return round((avg_safety + avg_eco) / 2, 1)


def _compute_prediction_score(db: Session, vehicle_id: int) -> float:
    """Compute prediction stability sub-score (0-100) from active predictions."""
    active_predictions = db.scalars(
        select(VehiclePrediction)
        .where(
            VehiclePrediction.vehicle_id == vehicle_id,
            VehiclePrediction.status == "active",
        )
    ).all()

    if not active_predictions:
        return 90.0  # No active risks = stable

    risk_weights = {"low": 1, "medium": 0.7, "high": 0.4, "critical": 0.2}
    total_weight = sum(risk_weights.get(p.risk_level, 0.5) for p in active_predictions)
    avg = total_weight / len(active_predictions)
    return round(max(30.0, min(100.0, avg * 100)), 1)


def compute_soul_score(db: Session, vehicle_id: int) -> VehicleSoulScore:
    """Compute the Vehicle Soul Score (VSS)."""
    identity = get_or_create_identity(db, vehicle_id)

    health = _compute_health_score(db, vehicle_id)
    memory = _compute_memory_score(db, vehicle_id)
    maintenance = _compute_maintenance_score(db, vehicle_id)
    driving = _compute_driving_score(db, vehicle_id)
    prediction = _compute_prediction_score(db, vehicle_id)

    w = _VSS_WEIGHTS
    score = (
        health * w["health"]
        + memory * w["memory"]
        + maintenance * w["maintenance"]
        + driving * w["driving"]
        + prediction * w["prediction"]
    )
    score = round(score, 1)

    grade, grade_label = _soul_grade(score)

    breakdown = SoulScoreBreakdown(
        health=round(health, 1),
        memory=round(memory, 1),
        maintenance=round(maintenance, 1),
        driving=round(driving, 1),
        prediction=round(prediction, 1),
        health_contribution=round(health * w["health"], 1),
        memory_contribution=round(memory * w["memory"], 1),
        maintenance_contribution=round(maintenance * w["maintenance"], 1),
        driving_contribution=round(driving * w["driving"], 1),
        prediction_contribution=round(prediction * w["prediction"], 1),
    )

    # Update life state with soul score
    life_state = db.scalar(
        select(VehicleLifeState).where(VehicleLifeState.vehicle_id == vehicle_id)
    )
    if life_state:
        life_state.soul_score = score
        life_state.health_score = health
        life_state.energy_health = health  # simplified
        life_state.mechanical_health = health
        db.flush()

    # Record in history
    db.add(VehicleSoulScoreHistory(
        vehicle_id=vehicle_id,
        soul_score=score,
        health_score=health,
        memory_score=memory,
        maintenance_score=maintenance,
        driving_score=driving,
        prediction_score=prediction,
        grade=grade,
    ))
    db.flush()

    return VehicleSoulScore(
        vehicle_id=vehicle_id,
        soul_id=identity.vehicle_uuid,
        score=score,
        grade=grade,
        grade_label=grade_label,
        breakdown=breakdown,
        computed_at=datetime.utcnow(),
    )


# ===========================================================================
# 3. Life State Management
# ===========================================================================

def update_life_state(db: Session, vehicle_id: int) -> VehicleLifeState:
    """Update the vehicle life state from current data."""
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise ValueError(f"Vehicle {vehicle_id} not found")

    identity = get_or_create_identity(db, vehicle_id)

    age_days = (date.today() - (vehicle.purchase_date or date.today())).days if vehicle.purchase_date else 0
    stage = _life_stage_for(age_days, vehicle.mileage)

    state = db.scalar(
        select(VehicleLifeState).where(VehicleLifeState.vehicle_id == vehicle_id)
    )
    if state is None:
        state = VehicleLifeState(vehicle_id=vehicle_id)
        db.add(state)

    state.life_stage = stage
    state.mileage = vehicle.mileage
    state.vehicle_age_days = age_days

    # Compute soul score to update health + soul
    soul = compute_soul_score(db, vehicle_id)
    state.soul_score = soul.score
    state.health_score = soul.breakdown.health

    db.flush()
    return state


def get_life_state(db: Session, vehicle_id: int) -> VehicleLifeState | None:
    return db.scalar(
        select(VehicleLifeState).where(VehicleLifeState.vehicle_id == vehicle_id)
    )


# ===========================================================================
# 4. Life Events
# ===========================================================================

def create_life_event(
    db: Session, vehicle_id: int, payload: VehicleLifeEventCreate
) -> VehicleLifeEvent:
    event = VehicleLifeEvent(
        vehicle_id=vehicle_id,
        event_type=payload.event_type,
        title=payload.title,
        description=payload.description,
        importance=payload.importance,
        mileage=payload.mileage,
        location=payload.location,
        cost=payload.cost,
        extra_data=payload.extra_data,
        event_time=payload.event_time or datetime.utcnow(),
    )
    db.add(event)
    db.flush()
    return event


def list_life_events(
    db: Session, vehicle_id: int, event_type: str | None = None, limit: int = 50
) -> list[VehicleLifeEvent]:
    stmt = (
        select(VehicleLifeEvent)
        .where(VehicleLifeEvent.vehicle_id == vehicle_id)
        .order_by(VehicleLifeEvent.event_time.desc())
        .limit(limit)
    )
    if event_type:
        stmt = stmt.where(VehicleLifeEvent.event_type == event_type)
    return list(db.scalars(stmt).all())


# ===========================================================================
# 5. Memory System
# ===========================================================================

def create_memory(
    db: Session, vehicle_id: int, payload: VehicleMemoryCreate
) -> VehicleMemory:
    memory = VehicleMemory(
        vehicle_id=vehicle_id,
        memory_type=payload.memory_type,
        content=payload.content,
        emotion_score=payload.emotion_score,
        importance=payload.importance,
        source=payload.source,
        meta_data=payload.meta_data,
    )
    db.add(memory)
    db.flush()
    return memory


def list_memories(
    db: Session, vehicle_id: int, memory_type: str | None = None, limit: int = 50
) -> list[VehicleMemory]:
    stmt = (
        select(VehicleMemory)
        .where(VehicleMemory.vehicle_id == vehicle_id)
        .order_by(VehicleMemory.created_time.desc())
        .limit(limit)
    )
    if memory_type:
        stmt = stmt.where(VehicleMemory.memory_type == memory_type)
    return list(db.scalars(stmt).all())


def search_memories(
    db: Session, vehicle_id: int, keyword: str, limit: int = 20
) -> list[VehicleMemory]:
    """Search memories by keyword in content."""
    return list(db.scalars(
        select(VehicleMemory)
        .where(
            VehicleMemory.vehicle_id == vehicle_id,
            VehicleMemory.content.ilike(f"%{keyword}%"),
        )
        .order_by(VehicleMemory.created_time.desc())
        .limit(limit)
    ).all())


# ===========================================================================
# 6. Health Metrics
# ===========================================================================

def create_health_metric(
    db: Session, vehicle_id: int, payload: VehicleHealthMetricsCreate
) -> VehicleHealthMetrics:
    metric = VehicleHealthMetrics(
        vehicle_id=vehicle_id,
        component=payload.component,
        health_score=payload.health_score,
        temperature=payload.temperature,
        wear_level=payload.wear_level,
        risk_level=payload.risk_level,
    )
    db.add(metric)
    db.flush()
    return metric


def list_health_metrics(
    db: Session, vehicle_id: int, component: str | None = None, limit: int = 50
) -> list[VehicleHealthMetrics]:
    stmt = (
        select(VehicleHealthMetrics)
        .where(VehicleHealthMetrics.vehicle_id == vehicle_id)
        .order_by(VehicleHealthMetrics.record_time.desc())
        .limit(limit)
    )
    if component:
        stmt = stmt.where(VehicleHealthMetrics.component == component)
    return list(db.scalars(stmt).all())


def get_latest_health_metrics(db: Session, vehicle_id: int) -> list[VehicleHealthMetrics]:
    """Get the latest health metric per component."""
    components = db.scalars(
        select(VehicleHealthMetrics.component)
        .where(VehicleHealthMetrics.vehicle_id == vehicle_id)
        .distinct()
    ).all()

    results = []
    for comp in components:
        latest = db.scalar(
            select(VehicleHealthMetrics)
            .where(
                VehicleHealthMetrics.vehicle_id == vehicle_id,
                VehicleHealthMetrics.component == comp,
            )
            .order_by(VehicleHealthMetrics.record_time.desc())
            .limit(1)
        )
        if latest:
            results.append(latest)
    return results


# ===========================================================================
# 7. Driver Profile
# ===========================================================================

def get_or_create_driver_profile(db: Session, vehicle_id: int) -> DriverProfile:
    profile = db.scalar(
        select(DriverProfile).where(DriverProfile.vehicle_id == vehicle_id)
    )
    if profile is not None:
        return profile
    profile = DriverProfile(vehicle_id=vehicle_id)
    db.add(profile)
    db.flush()
    return profile


def update_driver_profile_from_behavior(
    db: Session, vehicle_id: int
) -> DriverProfile:
    """Recompute driver profile from driving behavior data."""
    from app.models.driving_behavior import VehicleDrivingBehavior

    profile = get_or_create_driver_profile(db, vehicle_id)

    behaviors = db.scalars(
        select(VehicleDrivingBehavior)
        .where(VehicleDrivingBehavior.vehicle_id == vehicle_id)
        .order_by(VehicleDrivingBehavior.record_date.desc())
        .limit(90)
    ).all()

    if not behaviors:
        profile.driver_style = "balanced"
        profile.aggressive_score = 30.0
        profile.comfort_score = 75.0
        profile.eco_score = 75.0
        db.flush()
        return profile

    total_trips = sum(b.trip_count for b in behaviors)
    total_dist = sum(b.total_distance for b in behaviors)
    total_dur = sum(b.total_duration for b in behaviors)
    total_harsh = sum(
        b.harsh_acceleration_count + b.harsh_braking_count + b.sharp_turn_count
        for b in behaviors
    )

    avg_safety = sum(b.safety_score or 80 for b in behaviors) / len(behaviors)
    avg_eco = sum(b.eco_score or 80 for b in behaviors) / len(behaviors)

    # Harsh events per 100km
    harsh_per_100km = (total_harsh / max(1, total_dist)) * 100

    # Aggressive score: more harsh events = higher aggression
    aggressive = min(100.0, 20.0 + harsh_per_100km * 8)
    comfort = max(40.0, min(100.0, 100.0 - harsh_per_100km * 5))
    eco = avg_eco

    # Determine driver style
    if aggressive > 60:
        style = "aggressive"
    elif eco > 85:
        style = "eco"
    elif avg_safety > 90:
        style = "conservative"
    elif aggressive > 40 and avg_safety < 80:
        style = "sporty"
    else:
        style = "balanced"

    profile.driver_style = style
    profile.aggressive_score = round(aggressive, 1)
    profile.comfort_score = round(comfort, 1)
    profile.eco_score = round(eco, 1)
    profile.total_trips = total_trips
    profile.total_distance = round(total_dist, 1)
    profile.total_duration = total_dur
    profile.total_harsh_events = total_harsh

    # Preferred patterns
    if behaviors:
        speeds = [b.avg_speed or 40 for b in behaviors]
        avg_speed = sum(speeds) / len(speeds)
        profile.preferred_speed_range = f"{int(avg_speed * 0.7)}-{int(avg_speed * 1.3)}"

        # Driving time preference
        hours = [b.record_date for b in behaviors]
        profile.preferred_driving_time = "mixed"
        profile.preferred_road_type = "mixed"

    db.flush()
    return profile


# ===========================================================================
# 8. Predictions
# ===========================================================================

def create_prediction(
    db: Session, vehicle_id: int, payload: VehiclePredictionCreate
) -> VehiclePrediction:
    pred = VehiclePrediction(
        vehicle_id=vehicle_id,
        target_component=payload.target_component,
        prediction=payload.prediction,
        risk_level=payload.risk_level,
        confidence=payload.confidence,
        predicted_value=payload.predicted_value,
        predicted_unit=payload.predicted_unit,
        predicted_time=payload.predicted_time,
        root_cause=payload.root_cause,
        suggestion=payload.suggestion,
    )
    db.add(pred)
    db.flush()
    return pred


def list_predictions(
    db: Session, vehicle_id: int, status: str | None = None, limit: int = 20
) -> list[VehiclePrediction]:
    stmt = (
        select(VehiclePrediction)
        .where(VehiclePrediction.vehicle_id == vehicle_id)
        .order_by(VehiclePrediction.prediction_time.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(VehiclePrediction.status == status)
    return list(db.scalars(stmt).all())


# ===========================================================================
# 9. Sensor Stream
# ===========================================================================

def create_sensor_reading(
    db: Session, vehicle_id: int, sensor_name: str, value: float,
    unit: str | None = None, meta: dict | None = None,
) -> VehicleSensorStream:
    reading = VehicleSensorStream(
        vehicle_id=vehicle_id,
        sensor_name=sensor_name,
        value=value,
        unit=unit,
        meta=meta,
    )
    db.add(reading)
    db.flush()
    return reading


def list_sensor_stream(
    db: Session, vehicle_id: int, sensor_name: str | None = None,
    hours: int = 24, limit: int = 200,
) -> list[VehicleSensorStream]:
    since = datetime.utcnow() - timedelta(hours=hours)
    stmt = (
        select(VehicleSensorStream)
        .where(
            VehicleSensorStream.vehicle_id == vehicle_id,
            VehicleSensorStream.timestamp >= since,
        )
        .order_by(VehicleSensorStream.timestamp.desc())
        .limit(limit)
    )
    if sensor_name:
        stmt = stmt.where(VehicleSensorStream.sensor_name == sensor_name)
    return list(db.scalars(stmt).all())


# ===========================================================================
# 10. Soul Profile (旗舰聚合读模型)
# ===========================================================================

def get_soul_profile(db: Session, vehicle_id: int) -> SoulProfile | None:
    """Assemble the complete Soul Profile for a vehicle."""
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        return None

    identity = get_or_create_identity(db, vehicle_id)
    soul = compute_soul_score(db, vehicle_id)
    state = get_life_state(db, vehicle_id)

    if state is None:
        state = update_life_state(db, vehicle_id)

    # Life events
    events = list_life_events(db, vehicle_id, limit=20)

    # Memories
    memories = list_memories(db, vehicle_id, limit=20)

    # Health metrics
    health_metrics = get_latest_health_metrics(db, vehicle_id)

    # Predictions
    predictions = list_predictions(db, vehicle_id, status="active", limit=10)

    # Driver profile
    driver_profile = get_or_create_driver_profile(db, vehicle_id)

    # Companion days
    companion_days = state.vehicle_age_days or 0

    # AI insights
    insights = _generate_ai_insights(
        soul, state, events, memories, predictions, driver_profile
    )

    return SoulProfile(
        soul_id=identity.vehicle_uuid,
        vehicle_id=vehicle_id,
        name=vehicle.nickname or f"{vehicle.brand} {vehicle.model}",
        brand=vehicle.brand,
        model=vehicle.model,
        year=vehicle.year,
        energy_type=vehicle.fuel_type,
        nickname=vehicle.nickname,
        soul_score=soul.score,
        soul_grade=soul.grade,
        soul_grade_label=soul.grade_label,
        soul_breakdown=soul.breakdown,
        life_stage=state.life_stage,
        life_stage_label=_LIFE_STAGE_LABELS.get(state.life_stage, state.life_stage),
        health_score=state.health_score,
        energy_health=state.energy_health,
        mechanical_health=state.mechanical_health,
        software_health=state.software_health,
        companion_days=companion_days,
        mileage=vehicle.mileage,
        mileage_label=f"{vehicle.mileage:,} km",
        life_events=[VehicleLifeEventOut.model_validate(e) for e in events],
        life_events_count=db.scalar(
            select(func.count()).select_from(VehicleLifeEvent)
            .where(VehicleLifeEvent.vehicle_id == vehicle_id)
        ) or 0,
        memories=[VehicleMemoryOut.model_validate(m) for m in memories],
        memories_count=db.scalar(
            select(func.count()).select_from(VehicleMemory)
            .where(VehicleMemory.vehicle_id == vehicle_id)
        ) or 0,
        health_metrics=[VehicleHealthMetricsOut.model_validate(h) for h in health_metrics],
        predictions=[VehiclePredictionOut.model_validate(p) for p in predictions],
        driver_profile=DriverProfileOut.model_validate(driver_profile),
        driver_style_label=_DRIVER_STYLE_LABELS.get(
            driver_profile.driver_style, driver_profile.driver_style
        ),
        ai_insights=insights,
    )


def _generate_ai_insights(
    soul: VehicleSoulScore,
    state: VehicleLifeState,
    events: list[VehicleLifeEvent],
    memories: list[VehicleMemory],
    predictions: list[VehiclePrediction],
    driver_profile: DriverProfile,
) -> list[str]:
    """Generate human-readable AI insights from the soul profile data."""
    insights: list[str] = []

    # Soul score insight
    if soul.score >= 95:
        insights.append(f"灵魂指数 {soul.score} — 车辆处于传奇状态，所有维度表现卓越。")
    elif soul.score >= 80:
        insights.append(f"灵魂指数 {soul.score} — 车辆整体优秀，继续保持良好驾驶习惯。")
    elif soul.score >= 60:
        insights.append(f"灵魂指数 {soul.score} — 车辆运行正常，部分维度有提升空间。")
    else:
        insights.append(f"灵魂指数 {soul.score} — 车辆存在风险，建议全面检查。")

    # Weakest dimension
    b = soul.breakdown
    dims = [
        ("健康", b.health, b.health_contribution),
        ("记忆", b.memory, b.memory_contribution),
        ("维护", b.maintenance, b.maintenance_contribution),
        ("驾驶", b.driving, b.driving_contribution),
        ("预测", b.prediction, b.prediction_contribution),
    ]
    dims.sort(key=lambda x: x[1])
    weakest = dims[0]
    if weakest[1] < 70:
        insights.append(f"最薄弱维度: {weakest[0]}（{weakest[1]}），建议优先提升。")

    # High risk predictions
    high_risk = [p for p in predictions if p.risk_level in ("high", "critical")]
    if high_risk:
        insights.append(
            f"检测到 {len(high_risk)} 个高风险预测，"
            f"最紧急: {high_risk[0].prediction}"
        )

    # Driver style insight
    style_label = _DRIVER_STYLE_LABELS.get(
        driver_profile.driver_style, driver_profile.driver_style
    )
    if driver_profile.aggressive_score and driver_profile.aggressive_score > 60:
        insights.append(
            f"驾驶风格: {style_label}（激进指数 {driver_profile.aggressive_score}），"
            f"建议减少急加速和急刹车以提升驾驶评分。"
        )
    elif driver_profile.eco_score and driver_profile.eco_score > 85:
        insights.append(
            f"驾驶风格: {style_label}（节能指数 {driver_profile.eco_score}），"
            f"节能驾驶习惯优秀。"
        )

    # Memory richness
    if len(memories) >= 100:
        insights.append(f"车辆记忆丰富（{len(memories)} 条），AI对车辆理解深入。")
    elif len(memories) < 10:
        insights.append("车辆记忆较少，随着使用积累，AI将更了解您的驾驶习惯。")

    # Life stage
    stage_label = _LIFE_STAGE_LABELS.get(state.life_stage, state.life_stage)
    if state.life_stage == "AGING":
        insights.append(f"车辆已进入{stage_label}，建议增加保养频率。")
    elif state.life_stage == "NEW":
        insights.append(f"车辆处于{stage_label}，各项指标正在建立基线。")

    return insights


# ===========================================================================
# 11. Soul Score History
# ===========================================================================

def list_soul_score_history(
    db: Session, vehicle_id: int, limit: int = 30
) -> list[VehicleSoulScoreHistory]:
    return list(db.scalars(
        select(VehicleSoulScoreHistory)
        .where(VehicleSoulScoreHistory.vehicle_id == vehicle_id)
        .order_by(VehicleSoulScoreHistory.recorded_at.desc())
        .limit(limit)
    ).all())


# ===========================================================================
# 12. Create Digital Life (full lifecycle init)
# ===========================================================================

def create_digital_life(
    db: Session, vehicle_id: int
) -> CreateDigitalLifeResponse:
    """Initialize the digital life for a vehicle — creates identity + life state."""
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise ValueError(f"Vehicle {vehicle_id} not found")

    identity = get_or_create_identity(db, vehicle_id)
    update_life_state(db, vehicle_id)

    # Record the birth event
    existing_birth = db.scalar(
        select(VehicleLifeEvent).where(
            VehicleLifeEvent.vehicle_id == vehicle_id,
            VehicleLifeEvent.event_type == "PURCHASE",
        )
    )
    if existing_birth is None:
        create_life_event(db, vehicle_id, VehicleLifeEventCreate(
            event_type="PURCHASE",
            title="数字生命诞生",
            description=f"车辆 {vehicle.brand} {vehicle.model} 的数字生命正式诞生，灵魂ID: {identity.vehicle_uuid}",
            importance=10,
            mileage=vehicle.mileage,
            event_time=identity.birth_time or datetime.utcnow(),
        ))

    db.flush()

    return CreateDigitalLifeResponse(
        vehicle_id=vehicle_id,
        soul_id=identity.vehicle_uuid,
        message=f"数字生命已创建 — 灵魂ID: {identity.vehicle_uuid}",
        identity=VehicleIdentityOut.model_validate(identity),
    )
