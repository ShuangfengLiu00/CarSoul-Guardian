"""Risk-prediction closed-loop service (TASK010).

This is the bridge that turns the five-sub-agent workflow (which lives in
the ``carsoul_agent`` package) into a **persistent, auditable, self-
calibrating closed loop**:

    ┌─────────┐   ┌──────────┐   ┌─────────┐   ┌─────────┐
    │ assemble│──▶│ workflow │──▶│ persist │──▶│  alert  │
    │  state  │   │  (5 子)  │   │ predict │   │ (>=warn)│
    └─────────┘   └──────────┘   └─────────┘   └────┬────┘
         ▲                                            │
         │            ┌─────────┐   ┌─────────┐      ▼
         │            │accuracy │◀──│feedback │◀──┌──────┐
         └────────────│  stats  │   │ (close) │   │ user │
                      └─────────┘   └─────────┘   └──────┘

Responsibilities:
  * ``_assemble_state``  — read vehicle + latest health snapshot + digital
    twin telemetry + driving behaviour from the DB and shape them into the
    ``AgentState`` the workflow expects.
  * ``run_prediction``   — execute ``CoreWorkflow.run``, persist a
    ``RiskPrediction`` row, and (when level ≥ warning) create a
    ``VehicleAlert`` linked back to the prediction.
  * ``submit_feedback``  — **close the loop**: record the actual outcome,
    compute per-prediction accuracy, resolve the linked alert, and append a
    lifecycle event.
  * ``compute_accuracy`` — aggregate accuracy / false-alarm / missed rates
    so the loop's KPI is visible (and ready to feed calibration later).
  * ``patrol_all``       — proactive patrol: run a prediction for every
    active vehicle.

The service never calls an LLM directly — it delegates to the agent
package, preserving the architecture rule that AI logic stays there.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alert import VehicleAlert
from app.models.lifecycle_event import VehicleLifecycleEvent
from app.models.risk_prediction import RiskPrediction
from app.models.vehicle import Vehicle
from app.schemas.alert import AlertCreate
from app.services import (
    digital_twin_service,
    driving_behavior_service,
    health_service,
)

logger = logging.getLogger(__name__)

# ---- lazy import of the agent package (optional dependency) -------------- #
CoreWorkflow = None
_action_store = None


def _load_workflow():
    """Import CoreWorkflow lazily so a missing agent package never breaks boot."""
    global CoreWorkflow, _action_store
    if CoreWorkflow is not None:
        return True
    try:
        from carsoul_agent.agents.core import CoreWorkflow as _CW  # type: ignore
        from carsoul_agent.tools.guard_tools import action_store as _as  # type: ignore

        CoreWorkflow = _CW
        _action_store = _as
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("CoreWorkflow unavailable, predictions will be degraded: %s", exc)
        return False


# =========================================================================== #
#  Constants / helpers
# =========================================================================== #
# Map workflow risk level → alert level (VehicleAlert uses info|warning|critical).
_LEVEL_TO_ALERT_LEVEL = {
    "urgent": "critical",
    "warning": "warning",
    "info": "info",
}

# Outcomes that count as "the predicted risk materialised".
_CONFIRMING_OUTCOMES = {"confirmed", "partial"}


def _derive_driving_style(summary: dict) -> str:
    """Classify the driver profile from the behaviour summary."""
    safety = summary.get("avg_safety_score")
    eco = summary.get("avg_eco_score")
    trips = max(summary.get("trip_count", 0), 1)
    harsh_rate = summary.get("total_harsh_events", 0) / trips

    if safety is not None and safety < 75:
        return "aggressive"
    if harsh_rate > 2.0:
        return "aggressive"
    if eco is not None and eco >= 80:
        return "eco"
    return "balanced"


# =========================================================================== #
#  Stage 0 — calibration context (自纠错校准上下文)
# =========================================================================== #
def _build_calibration_context(db: Session, vehicle_id: int, limit: int = 10) -> dict[str, Any]:
    """读取已闭环的预测反馈，构建自纠错校准上下文。

    供 ``_assemble_state`` 注入 ``AgentState["calibration_context"]``，
    让主动巡检路径也能享受与用户触发路径一致的「从反馈中学习」。
    """
    stmt = (
        select(RiskPrediction)
        .where(
            RiskPrediction.vehicle_id == vehicle_id,
            RiskPrediction.actual_outcome.is_not(None),
        )
        .order_by(RiskPrediction.created_at.desc())
        .limit(limit)
    )
    rows = list(db.scalars(stmt).all())

    if not rows:
        return {
            "vehicle_id": vehicle_id,
            "has_history": False,
            "total_feedback": 0,
            "false_alarm_rate": None,
            "confirmed_rate": None,
            "accuracy_rate": None,
            "recent_feedbacks": [],
            "calibration_note": "暂无历史反馈，本次评估使用默认置信度。",
        }

    total = len(rows)
    false_alarms = sum(1 for r in rows if r.actual_outcome == "false_alarm")
    confirmed = sum(1 for r in rows if r.actual_outcome == "confirmed")
    accurate = sum(1 for r in rows if (r.accuracy or 0) >= 1.0)

    false_alarm_rate = round(false_alarms / total, 3) if total else None
    confirmed_rate = round(confirmed / total, 3) if total else None
    accuracy_rate = round(accurate / total, 3) if total else None

    recent_feedbacks = [
        {
            "prediction_id": r.id,
            "predicted_level": r.predicted_level,
            "root_cause": r.root_cause,
            "primary_type": r.primary_type,
            "actual_outcome": r.actual_outcome,
            "accuracy": r.accuracy,
            "outcome_notes": r.outcome_notes,
        }
        for r in rows
    ]

    if false_alarm_rate is not None and false_alarm_rate >= 0.4:
        calibration_note = (
            f"历史误报率 {false_alarm_rate * 100:.0f}% 偏高，"
            f"本次评估已下调置信度、放宽ETA窗口，避免过度预警。"
        )
    elif accuracy_rate is not None and accuracy_rate >= 0.8:
        calibration_note = (
            f"历史预测准确率 {accuracy_rate * 100:.0f}% 良好，"
            f"本次评估维持标准置信度。"
        )
    else:
        calibration_note = "历史反馈数据有限，本次评估使用标准置信度。"

    return {
        "vehicle_id": vehicle_id,
        "has_history": True,
        "total_feedback": total,
        "false_alarm_rate": false_alarm_rate,
        "confirmed_rate": confirmed_rate,
        "accuracy_rate": accuracy_rate,
        "recent_feedbacks": recent_feedbacks,
        "calibration_note": calibration_note,
    }


# =========================================================================== #
#  Stage 1 — data assembly
# =========================================================================== #
def _assemble_state(db: Session, vehicle_id: int) -> dict[str, Any]:
    """Build the ``AgentState`` the five-sub-agent workflow consumes.

    Pulls from four data sources:
      * Vehicle            → identity + mileage
      * HealthSnapshot     → health_score + per-item risks
      * DigitalTwin        → telemetry (sensor readings)
      * DrivingBehavior    → driver profile (driving_style)
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise ValueError(f"Vehicle {vehicle_id} not found")

    # ---- health snapshot + items ----
    snap = health_service.get_latest_snapshot(db, vehicle_id)
    health_score = snap.health_score if snap else 80
    risks: list[dict] = []
    if snap is not None:
        items = health_service.get_items(db, snap.id)
        _LEVEL_MAP = {"critical": "urgent", "warning": "warning", "info": "info", "ok": "info"}
        for it in items:
            level = _LEVEL_MAP.get(it.level, "info")
            if level in ("warning", "urgent"):
                risks.append({
                    "category": it.category,
                    "item": it.item_name,
                    "level": level,
                    "detail": it.detail or "",
                    "recommendation": it.recommendation,
                })

    # ---- vehicle state (the "vehicle twin" snapshot) ----
    vehicle_state: dict[str, Any] = {
        "vehicle_id": vehicle.id,
        "brand": vehicle.brand,
        "model": vehicle.model,
        "year": vehicle.year,
        "mileage": vehicle.mileage,
        "fuel_type": vehicle.fuel_type,
        "health_score": health_score,
        "risks": risks,
    }

    # ---- sensor window (from digital twin telemetry) ----
    sensor_window: list[dict] = []
    twin = digital_twin_service.get_twin(db, vehicle_id)
    if twin is not None and twin.telemetry:
        reading = dict(twin.telemetry)
        # Ensure health_score is present so the perception rule engine can use it.
        reading.setdefault("health_score", health_score)
        sensor_window.append(reading)
    elif risks or health_score is not None:
        # No twin yet — still feed the health score so perception can run.
        sensor_window.append({"health_score": health_score})

    # ---- driver profile (the "driver twin") ----
    behavior_summary = driving_behavior_service.get_behavior_summary(db, vehicle_id, days=30)
    driver_profile: dict[str, Any] = {
        "driving_style": _derive_driving_style(behavior_summary),
        "safety_score": behavior_summary.get("avg_safety_score"),
        "eco_score": behavior_summary.get("avg_eco_score"),
        "harsh_events": behavior_summary.get("total_harsh_events", 0),
        "trip_count": behavior_summary.get("trip_count", 0),
    }

    # ---- 自纠错校准上下文（主动巡检路径也加载历史反馈）----
    # 主动巡检经过 _assemble_state 而非 carsoul_agent._build_initial_state，
    # 因此这里也要注入 calibration_context，让无人交互的巡检也能自纠错。
    calibration_context = _build_calibration_context(db, vehicle_id)

    return {
        "vehicle_state": vehicle_state,
        "sensor_window": sensor_window,
        "driver_profile": driver_profile,
        "calibration_context": calibration_context,
        "user_message": "",
        "trace_log": [],
    }


# =========================================================================== #
#  Stage 2 — run prediction + persist + alert
# =========================================================================== #
def run_prediction(
    db: Session, vehicle_id: int, triggered_by: str = "user"
) -> RiskPrediction:
    """Execute the closed-loop forward path for one vehicle.

    Returns the persisted ``RiskPrediction``. When the predicted level is
    ``warning`` or ``urgent`` a ``VehicleAlert`` is created and linked.

    主动巡检（``triggered_by="patrol"``）带去重：如果同一车辆已有未闭环的
    同类风险预测（primary_type + root_cause + level 相同），或上一条巡检
    结果也是正常，则不重复创建记录，直接返回已有预测。用户手动触发的预测
    始终创建新记录。
    """
    if db.get(Vehicle, vehicle_id) is None:
        raise ValueError(f"Vehicle {vehicle_id} not found")

    state = _assemble_state(db, vehicle_id)

    # Run the five-sub-agent workflow (offline rule-based by default).
    if _load_workflow() and _action_store is not None:
        _action_store.clear()  # avoid cross-run contamination
        try:
            final_state = CoreWorkflow.run(state)
        except Exception as exc:  # noqa: BLE001
            logger.exception("CoreWorkflow run failed: %s", exc)
            final_state = state
    else:
        # Degraded mode: no agent package — record a minimal normal prediction.
        final_state = {
            **state,
            "is_normal": True,
            "anomalies": [],
            "trace_log": state.get("trace_log", []),
        }

    # Patrol dedup: don't flood the history with identical predictions.
    if triggered_by == "patrol":
        existing = _find_patrol_duplicate(db, vehicle_id, final_state)
        if existing is not None:
            logger.info(
                "Patrol dedup: vehicle %s already has open prediction %s "
                "with same signature, skipping.",
                vehicle_id, existing.id,
            )
            return existing

    return _persist_prediction(db, vehicle_id, triggered_by, final_state)


def _find_patrol_duplicate(
    db: Session, vehicle_id: int, state: dict[str, Any]
) -> RiskPrediction | None:
    """Check if an existing open prediction matches the new workflow result.

    For anomalies: match on primary_type + root_cause + predicted_level.
    For normal results: match if the most recent prediction is also normal
    and still open (no need to record "all clear" every 30 minutes).
    """
    is_normal = bool(state.get("is_normal", False))

    if is_normal:
        # If the latest prediction is already normal & open, skip.
        stmt = (
            select(RiskPrediction)
            .where(
                RiskPrediction.vehicle_id == vehicle_id,
                RiskPrediction.status.in_(["open", "acknowledged"]),
                RiskPrediction.is_normal.is_(True),
            )
            .order_by(RiskPrediction.created_at.desc())
            .limit(1)
        )
        return db.scalar(stmt)

    # Anomaly: match on signature.
    risk = state.get("risk_assessment", {}) or {}
    diagnosis = state.get("diagnosis", {}) or {}
    primary = diagnosis.get("primary", {}) or {}
    level = risk.get("level", "warning")
    primary_type = risk.get("primary_type") or primary.get("type")
    root_cause = primary.get("root_cause")

    stmt = (
        select(RiskPrediction)
        .where(
            RiskPrediction.vehicle_id == vehicle_id,
            RiskPrediction.status.in_(["open", "acknowledged"]),
            RiskPrediction.is_normal.is_(False),
            RiskPrediction.predicted_level == level,
        )
        .order_by(RiskPrediction.created_at.desc())
    )
    for cand in db.scalars(stmt):
        # Compare signature (NULL-safe: both None counts as match).
        if cand.primary_type == primary_type and cand.root_cause == root_cause:
            return cand
    return None


def _persist_prediction(
    db: Session,
    vehicle_id: int,
    triggered_by: str,
    state: dict[str, Any],
) -> RiskPrediction:
    """Translate the final workflow state into a persisted prediction + alert."""
    is_normal = bool(state.get("is_normal", False))
    risk = state.get("risk_assessment", {}) or {}
    diagnosis = state.get("diagnosis", {}) or {}
    primary = diagnosis.get("primary", {}) or {}
    explanation = state.get("explanation", "")
    anomalies = state.get("anomalies", []) or []
    trace_log = state.get("trace_log", []) or []

    level = risk.get("level", "info" if is_normal else "warning")
    actions_hint = primary.get("actions_hint", []) or []

    prediction = RiskPrediction(
        vehicle_id=vehicle_id,
        triggered_by=triggered_by,
        is_normal=is_normal,
        predicted_level=level,
        predicted_probability=risk.get("probability_percent"),
        predicted_eta_hours=risk.get("eta_hours"),
        primary_type=risk.get("primary_type") or primary.get("type"),
        root_cause=primary.get("root_cause"),
        trend=risk.get("trend"),
        explanation=explanation,
        actions_hint=actions_hint,
        anomalies_count=len(anomalies),
        trace_log=list(trace_log),
        status="open",
    )

    # Create an alert when the risk is actionable.
    if level in ("warning", "urgent") and not is_normal:
        alert = _create_alert_from_prediction(
            db, vehicle_id, level, primary, explanation, actions_hint
        )
        prediction.alert_id = alert.id

    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def _create_alert_from_prediction(
    db: Session,
    vehicle_id: int,
    level: str,
    primary: dict,
    explanation: str,
    actions_hint: list[str],
) -> VehicleAlert:
    """Materialise a VehicleAlert from a high-risk prediction."""
    alert_level = _LEVEL_TO_ALERT_LEVEL.get(level, "warning")
    root_cause = primary.get("root_cause", "车辆风险")
    recommendation = "；".join(actions_hint) if actions_hint else None

    payload = AlertCreate(
        alert_type="health",
        level=alert_level,
        category=primary.get("type", "overall"),
        title=f"风险预警：{root_cause}",
        detail=explanation or None,
        recommendation=recommendation,
    )
    alert = VehicleAlert(**payload.model_dump(), vehicle_id=vehicle_id)
    db.add(alert)
    db.flush()  # get the id without committing yet
    return alert


# =========================================================================== #
#  Stage 3 — query
# =========================================================================== #
def list_predictions(
    db: Session,
    vehicle_id: int,
    status: str | None = None,
    limit: int = 50,
) -> list[RiskPrediction]:
    stmt = select(RiskPrediction).where(RiskPrediction.vehicle_id == vehicle_id)
    if status:
        stmt = stmt.where(RiskPrediction.status == status)
    stmt = stmt.order_by(RiskPrediction.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def get_prediction(db: Session, prediction_id: int) -> RiskPrediction | None:
    return db.get(RiskPrediction, prediction_id)


def acknowledge_prediction(db: Session, prediction_id: int) -> RiskPrediction | None:
    pred = db.get(RiskPrediction, prediction_id)
    if pred is None or pred.status != "open":
        return pred
    pred.status = "acknowledged"
    pred.acknowledged_at = datetime.utcnow()
    db.commit()
    db.refresh(pred)
    return pred


# =========================================================================== #
#  Stage 4 — feedback (the loop closure)
# =========================================================================== #
def _compute_accuracy(is_normal: bool, outcome: str) -> float:
    """Per-prediction accuracy in [0.0, 0.5, 1.0].

    * anomaly predicted + confirmed        → 1.0 (hit)
    * anomaly predicted + false_alarm/no   → 0.0 (false alarm)
    * anomaly predicted + partial          → 0.5
    * normal predicted  + no_event/false   → 1.0 (correctly calm)
    * normal predicted  + confirmed        → 0.0 (missed)
    * normal predicted  + partial          → 0.5
    """
    if is_normal:
        if outcome in ("no_event", "false_alarm"):
            return 1.0
        if outcome == "confirmed":
            return 0.0
        return 0.5
    # anomaly predicted
    if outcome == "confirmed":
        return 1.0
    if outcome in ("false_alarm", "no_event"):
        return 0.0
    return 0.5


def submit_feedback(
    db: Session,
    prediction_id: int,
    actual_outcome: str,
    outcome_notes: str | None = None,
) -> RiskPrediction | None:
    """Close the loop: record the actual outcome and compute accuracy.

    Side effects:
      * prediction → status ``resolved``, accuracy set
      * linked alert → ``resolved``
      * a lifecycle event appended to the vehicle's archive
    """
    pred = db.get(RiskPrediction, prediction_id)
    if pred is None:
        return None
    if pred.status == "resolved":
        raise ValueError("该预测已闭环，不可重复提交反馈")

    valid = {"confirmed", "false_alarm", "no_event", "partial"}
    if actual_outcome not in valid:
        raise ValueError(f"无效的处置结果，应为 {valid}")

    pred.actual_outcome = actual_outcome
    pred.outcome_notes = outcome_notes
    pred.accuracy = _compute_accuracy(pred.is_normal, actual_outcome)
    pred.status = "resolved"
    pred.resolved_at = datetime.utcnow()
    if pred.acknowledged_at is None:
        pred.acknowledged_at = pred.resolved_at

    # Resolve the linked alert.
    if pred.alert_id is not None:
        alert = db.get(VehicleAlert, pred.alert_id)
        if alert is not None and alert.status != "resolved":
            alert.status = "resolved"
            alert.resolved_at = datetime.utcnow()
            if alert.acknowledged_at is None:
                alert.acknowledged_at = alert.resolved_at

    db.flush()

    # Record a lifecycle event — the audit trail of the loop closure.
    _record_feedback_lifecycle(db, pred, actual_outcome)

    db.commit()
    db.refresh(pred)
    return pred


def _record_feedback_lifecycle(
    db: Session, pred: RiskPrediction, outcome: str
) -> None:
    """Append a lifecycle event capturing the prediction's outcome."""
    outcome_label = {
        "confirmed": "风险已证实",
        "false_alarm": "误报",
        "no_event": "未发生",
        "partial": "部分发生",
    }.get(outcome, outcome)

    title = f"风险预测闭环：{outcome_label}"
    detail = (
        f"预测等级 {pred.predicted_level}"
        f"（{pred.root_cause or '正常'}）"
        f"→ 实际 {outcome_label}，准确率 {pred.accuracy:.2f}。"
    )
    if pred.outcome_notes:
        detail += f" 备注：{pred.outcome_notes}"

    event = VehicleLifecycleEvent(
        vehicle_id=pred.vehicle_id,
        event_type="guard_intervention",
        title=title,
        description=detail,
        event_date=datetime.utcnow().date(),
        severity=pred.predicted_level if pred.predicted_level != "info" else "info",
        extra_data={
            "prediction_id": pred.id,
            "actual_outcome": outcome,
            "accuracy": pred.accuracy,
        },
    )
    db.add(event)


# =========================================================================== #
#  Stage 5 — accuracy stats (the loop KPI)
# =========================================================================== #
def compute_accuracy(db: Session, vehicle_id: int) -> dict[str, Any]:
    """Aggregate prediction accuracy for a vehicle."""
    total = db.scalar(
        select(func.count(RiskPrediction.id)).where(
            RiskPrediction.vehicle_id == vehicle_id
        )
    ) or 0
    resolved = db.scalar(
        select(func.count(RiskPrediction.id)).where(
            RiskPrediction.vehicle_id == vehicle_id,
            RiskPrediction.status == "resolved",
        )
    ) or 0
    with_feedback = db.scalar(
        select(func.count(RiskPrediction.id)).where(
            RiskPrediction.vehicle_id == vehicle_id,
            RiskPrediction.actual_outcome.is_not(None),
        )
    ) or 0

    # Load feedback rows to classify.
    stmt = select(RiskPrediction).where(
        RiskPrediction.vehicle_id == vehicle_id,
        RiskPrediction.actual_outcome.is_not(None),
    )
    rows = list(db.scalars(stmt).all())

    accurate = sum(1 for r in rows if (r.accuracy or 0) >= 1.0)
    false_alarms = sum(
        1 for r in rows if not r.is_normal and (r.accuracy or 0) <= 0.0
    )
    missed = sum(1 for r in rows if r.is_normal and (r.accuracy or 0) <= 0.0)

    accuracy_rate = round(accurate / with_feedback, 3) if with_feedback else None
    anomaly_feedback = sum(1 for r in rows if not r.is_normal)
    false_alarm_rate = (
        round(false_alarms / anomaly_feedback, 3) if anomaly_feedback else None
    )

    # Breakdown by predicted level.
    by_level: dict[str, dict[str, int]] = {}
    for r in rows:
        bucket = by_level.setdefault(r.predicted_level, {"total": 0, "accurate": 0})
        bucket["total"] += 1
        if (r.accuracy or 0) >= 1.0:
            bucket["accurate"] += 1

    return {
        "vehicle_id": vehicle_id,
        "total_predictions": total,
        "resolved_predictions": resolved,
        "with_feedback": with_feedback,
        "accurate": accurate,
        "false_alarms": false_alarms,
        "missed": missed,
        "accuracy_rate": accuracy_rate,
        "false_alarm_rate": false_alarm_rate,
        "by_level": by_level,
    }


# =========================================================================== #
#  Stage 6 — proactive patrol
# =========================================================================== #
def patrol_all(db: Session) -> dict[str, Any]:
    """Run a prediction for every active vehicle (主动巡检)."""
    stmt = select(Vehicle).where(Vehicle.status == "active").order_by(Vehicle.id)
    vehicles = list(db.scalars(stmt).all())

    patrol_started = datetime.utcnow()
    patrolled = 0
    predictions_made = 0
    alerts_generated = 0
    deduped = 0
    details: list[dict[str, Any]] = []

    for v in vehicles:
        patrolled += 1
        try:
            pred = run_prediction(db, v.id, triggered_by="patrol")
            # A prediction created before this patrol started is a dedup hit.
            is_new = pred.created_at >= patrol_started if pred.created_at else True
            if is_new:
                predictions_made += 1
                if pred.alert_id is not None:
                    alerts_generated += 1
            else:
                deduped += 1
            details.append({
                "vehicle_id": v.id,
                "vehicle": f"{v.brand} {v.model}",
                "prediction_id": pred.id,
                "level": pred.predicted_level,
                "is_normal": pred.is_normal,
                "alert_id": pred.alert_id,
                "deduped": not is_new,
                "status": "ok",
            })
        except Exception as exc:  # noqa: BLE001
            logger.exception("Patrol failed for vehicle %s: %s", v.id, exc)
            details.append({
                "vehicle_id": v.id,
                "vehicle": f"{v.brand} {v.model}",
                "status": "error",
                "error": str(exc),
            })

    return {
        "patrolled": patrolled,
        "predictions_made": predictions_made,
        "alerts_generated": alerts_generated,
        "deduped": deduped,
        "details": details,
    }
