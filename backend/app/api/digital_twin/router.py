"""Digital Twin API — Vehicle Digital Life Engine endpoints (TASK007-V2).

RESTful routes for the Vehicle Digital Life Engine:

  POST /api/digital-twin/create                    — 创建数字生命
  GET  /api/digital-twin/{id}/profile              — 灵魂档案
  GET  /api/digital-twin/{id}/soul-score           — VSS 灵魂指数
  GET  /api/digital-twin/{id}/life-state            — 生命状态
  GET/POST /api/digital-twin/{id}/life-events       — 生命事件
  GET/POST /api/digital-twin/{id}/memories          — 记忆系统
  GET/POST /api/digital-twin/{id}/health-metrics    — 健康指标
  GET  /api/digital-twin/{id}/predictions          — AI预测
  GET  /api/digital-twin/{id}/driver-profile        — 驾驶人格
  GET  /api/digital-twin/{id}/soul-history          — VSS历史
  POST /api/digital-twin/{id}/agent/{agent_type}    — Agent接口
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.vehicle import Vehicle
from app.schemas.digital_life import (
    AgentQueryRequest,
    AgentQueryResponse,
    CreateDigitalLifeResponse,
    DriverProfileOut,
    SoulProfile,
    VehicleHealthMetricsCreate,
    VehicleHealthMetricsList,
    VehicleHealthMetricsOut,
    VehicleLifeEventCreate,
    VehicleLifeEventList,
    VehicleLifeEventOut,
    VehicleLifeStateOut,
    VehicleMemoryCreate,
    VehicleMemoryList,
    VehicleMemoryOut,
    VehiclePredictionCreate,
    VehiclePredictionList,
    VehiclePredictionOut,
    VehicleSoulScore,
    VehicleSoulScoreHistoryList,
    VehicleSoulScoreHistoryOut,
)
from app.services import lifecycle_generator, soul_engine_service
from app.utils.logger import logger

router = APIRouter()


def _get_vehicle_or_404(db: Session, vehicle_id: int) -> Vehicle:
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(404, "Vehicle not found")
    return vehicle


# ===========================================================================
# Create Digital Life
# ===========================================================================

@router.post("/create", response_model=CreateDigitalLifeResponse, status_code=201)
def create_digital_life(
    vehicle_id: int = Query(..., description="车辆ID"),
    db: Session = Depends(get_db),
) -> CreateDigitalLifeResponse:
    """创建车辆数字生命 — 生成灵魂ID并初始化生命状态."""
    _get_vehicle_or_404(db, vehicle_id)
    try:
        result = soul_engine_service.create_digital_life(db, vehicle_id)
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(400, str(exc))


# ===========================================================================
# Soul Profile (旗舰读模型)
# ===========================================================================

@router.get("/{vehicle_id}/profile", response_model=SoulProfile)
def get_soul_profile(
    vehicle_id: int, db: Session = Depends(get_db)
) -> SoulProfile:
    """获取车辆灵魂档案 — 聚合所有数字生命数据的旗舰视图."""
    profile = soul_engine_service.get_soul_profile(db, vehicle_id)
    if profile is None:
        raise HTTPException(404, "Vehicle not found")
    return profile


# ===========================================================================
# Soul Score (VSS)
# ===========================================================================

@router.get("/{vehicle_id}/soul-score", response_model=VehicleSoulScore)
def get_soul_score(
    vehicle_id: int, db: Session = Depends(get_db)
) -> VehicleSoulScore:
    """计算车辆灵魂指数 VSS — Health×40% + Memory×15% + Maintenance×15% + Driving×15% + Prediction×15%."""
    _get_vehicle_or_404(db, vehicle_id)
    return soul_engine_service.compute_soul_score(db, vehicle_id)


@router.get("/{vehicle_id}/soul-history", response_model=VehicleSoulScoreHistoryList)
def get_soul_history(
    vehicle_id: int,
    limit: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> VehicleSoulScoreHistoryList:
    """获取VSS灵魂指数历史轨迹."""
    _get_vehicle_or_404(db, vehicle_id)
    items = soul_engine_service.list_soul_score_history(db, vehicle_id, limit)
    out = [VehicleSoulScoreHistoryOut.model_validate(h) for h in items]
    return VehicleSoulScoreHistoryList(items=out, total=len(out))


# ===========================================================================
# Life State
# ===========================================================================

@router.get("/{vehicle_id}/life-state", response_model=VehicleLifeStateOut)
def get_life_state(
    vehicle_id: int, db: Session = Depends(get_db)
) -> VehicleLifeStateOut:
    """获取车辆当前生命状态."""
    _get_vehicle_or_404(db, vehicle_id)
    state = soul_engine_service.get_life_state(db, vehicle_id)
    if state is None:
        state = soul_engine_service.update_life_state(db, vehicle_id)
        db.flush()
    return VehicleLifeStateOut.model_validate(state)


@router.post("/{vehicle_id}/life-state/refresh", response_model=VehicleLifeStateOut)
def refresh_life_state(
    vehicle_id: int, db: Session = Depends(get_db)
) -> VehicleLifeStateOut:
    """刷新车辆生命状态 — 重新计算生命阶段和灵魂指数."""
    _get_vehicle_or_404(db, vehicle_id)
    state = soul_engine_service.update_life_state(db, vehicle_id)
    db.commit()
    return VehicleLifeStateOut.model_validate(state)


# ===========================================================================
# Life Events
# ===========================================================================

@router.get("/{vehicle_id}/life-events", response_model=VehicleLifeEventList)
def list_life_events(
    vehicle_id: int,
    event_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> VehicleLifeEventList:
    """获取车辆生命事件时间线."""
    _get_vehicle_or_404(db, vehicle_id)
    items = soul_engine_service.list_life_events(db, vehicle_id, event_type, limit)
    out = [VehicleLifeEventOut.model_validate(e) for e in items]
    return VehicleLifeEventList(items=out, total=len(out))


@router.post("/{vehicle_id}/life-events", response_model=VehicleLifeEventOut, status_code=201)
def create_life_event(
    vehicle_id: int,
    payload: VehicleLifeEventCreate,
    db: Session = Depends(get_db),
) -> VehicleLifeEventOut:
    """创建车辆生命事件."""
    _get_vehicle_or_404(db, vehicle_id)
    event = soul_engine_service.create_life_event(db, vehicle_id, payload)
    db.commit()
    return VehicleLifeEventOut.model_validate(event)


# ===========================================================================
# Memory System
# ===========================================================================

@router.get("/{vehicle_id}/memories", response_model=VehicleMemoryList)
def list_memories(
    vehicle_id: int,
    memory_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> VehicleMemoryList:
    """获取车辆记忆列表."""
    _get_vehicle_or_404(db, vehicle_id)
    items = soul_engine_service.list_memories(db, vehicle_id, memory_type, limit)
    out = [VehicleMemoryOut.model_validate(m) for m in items]
    return VehicleMemoryList(items=out, total=len(out))


@router.post("/{vehicle_id}/memories", response_model=VehicleMemoryOut, status_code=201)
def create_memory(
    vehicle_id: int,
    payload: VehicleMemoryCreate,
    db: Session = Depends(get_db),
) -> VehicleMemoryOut:
    """创建车辆记忆 — 让AI积累对车辆的认知."""
    _get_vehicle_or_404(db, vehicle_id)
    memory = soul_engine_service.create_memory(db, vehicle_id, payload)
    db.commit()
    return VehicleMemoryOut.model_validate(memory)


@router.get("/{vehicle_id}/memories/search", response_model=VehicleMemoryList)
def search_memories(
    vehicle_id: int,
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> VehicleMemoryList:
    """搜索车辆记忆 — AI上下文检索."""
    _get_vehicle_or_404(db, vehicle_id)
    items = soul_engine_service.search_memories(db, vehicle_id, q, limit)
    out = [VehicleMemoryOut.model_validate(m) for m in items]
    return VehicleMemoryList(items=out, total=len(out))


# ===========================================================================
# Health Metrics
# ===========================================================================

@router.get("/{vehicle_id}/health-metrics", response_model=VehicleHealthMetricsList)
def list_health_metrics(
    vehicle_id: int,
    component: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> VehicleHealthMetricsList:
    """获取车辆健康指标 — 组件级细分健康."""
    _get_vehicle_or_404(db, vehicle_id)
    items = soul_engine_service.list_health_metrics(db, vehicle_id, component, limit)
    out = [VehicleHealthMetricsOut.model_validate(h) for h in items]
    return VehicleHealthMetricsList(items=out, total=len(out))


@router.post("/{vehicle_id}/health-metrics", response_model=VehicleHealthMetricsOut, status_code=201)
def create_health_metric(
    vehicle_id: int,
    payload: VehicleHealthMetricsCreate,
    db: Session = Depends(get_db),
) -> VehicleHealthMetricsOut:
    """记录车辆健康指标."""
    _get_vehicle_or_404(db, vehicle_id)
    metric = soul_engine_service.create_health_metric(db, vehicle_id, payload)
    db.commit()
    return VehicleHealthMetricsOut.model_validate(metric)


# ===========================================================================
# Predictions
# ===========================================================================

@router.get("/{vehicle_id}/predictions", response_model=VehiclePredictionList)
def list_predictions(
    vehicle_id: int,
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> VehiclePredictionList:
    """获取AI预测结果列表."""
    _get_vehicle_or_404(db, vehicle_id)
    items = soul_engine_service.list_predictions(db, vehicle_id, status, limit)
    out = [VehiclePredictionOut.model_validate(p) for p in items]
    return VehiclePredictionList(items=out, total=len(out))


@router.post("/{vehicle_id}/predictions", response_model=VehiclePredictionOut, status_code=201)
def create_prediction(
    vehicle_id: int,
    payload: VehiclePredictionCreate,
    db: Session = Depends(get_db),
) -> VehiclePredictionOut:
    """创建AI预测结果."""
    _get_vehicle_or_404(db, vehicle_id)
    pred = soul_engine_service.create_prediction(db, vehicle_id, payload)
    db.commit()
    return VehiclePredictionOut.model_validate(pred)


# ===========================================================================
# Driver Profile
# ===========================================================================

@router.get("/{vehicle_id}/driver-profile", response_model=DriverProfileOut)
def get_driver_profile(
    vehicle_id: int, db: Session = Depends(get_db)
) -> DriverProfileOut:
    """获取驾驶人格模型."""
    _get_vehicle_or_404(db, vehicle_id)
    profile = soul_engine_service.get_or_create_driver_profile(db, vehicle_id)
    return DriverProfileOut.model_validate(profile)


@router.post("/{vehicle_id}/driver-profile/refresh", response_model=DriverProfileOut)
def refresh_driver_profile(
    vehicle_id: int, db: Session = Depends(get_db)
) -> DriverProfileOut:
    """刷新驾驶人格 — 从驾驶行为数据重新计算."""
    _get_vehicle_or_404(db, vehicle_id)
    profile = soul_engine_service.update_driver_profile_from_behavior(db, vehicle_id)
    db.commit()
    return DriverProfileOut.model_validate(profile)


# ===========================================================================
# Agent Interface (future hooks)
# ===========================================================================

@router.post("/{vehicle_id}/agent/{agent_type}", response_model=AgentQueryResponse)
def agent_query(
    vehicle_id: int,
    agent_type: str,
    payload: AgentQueryRequest,
    db: Session = Depends(get_db),
) -> AgentQueryResponse:
    """AI Agent 统一查询接口 — 支持三种Agent: doctor | maintenance | insurance.

    这是Agent接口预留层，当前返回基于灵魂档案的规则化响应。
    未来将接入完整的 AI Agent 链路。
    """
    _get_vehicle_or_404(db, vehicle_id)

    if agent_type not in ("doctor", "maintenance", "insurance"):
        raise HTTPException(400, f"Unknown agent type: {agent_type}. Use: doctor | maintenance | insurance")

    profile = soul_engine_service.get_soul_profile(db, vehicle_id)
    if profile is None:
        raise HTTPException(404, "Soul profile not found")

    # Rule-based responses per agent type
    if agent_type == "doctor":
        answer = _doctor_agent_response(profile)
    elif agent_type == "maintenance":
        answer = _maintenance_agent_response(profile)
    else:
        answer = _insurance_agent_response(profile)

    logger.info("Agent [{}] query for vehicle {}: {}", agent_type, vehicle_id, payload.query[:80])

    return AgentQueryResponse(
        agent_type=agent_type,
        answer=answer,
        confidence=0.85,
        suggestions=profile.ai_insights[:3],
        data={
            "soul_score": profile.soul_score,
            "life_stage": profile.life_stage,
            "health_score": profile.health_score,
        },
    )


# ===========================================================================
# 365-day Lifecycle Generator
# ===========================================================================

@router.post("/{vehicle_id}/generate-lifecycle")
def generate_lifecycle(
    vehicle_id: int,
    force: bool = Query(False, description="强制重新生成（覆盖现有数据）"),
    db: Session = Depends(get_db),
) -> dict:
    """生成365天数字生命周期数据 — 健康指标、传感器、生命事件、记忆、预测、VSS."""
    _get_vehicle_or_404(db, vehicle_id)
    try:
        result = lifecycle_generator.generate_365_day_lifecycle(db, vehicle_id, force=force)
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))


def _doctor_agent_response(profile: SoulProfile) -> str:
    """AI车辆医生Agent — 基于灵魂档案的健康诊断."""
    lines = [
        f"我是您的AI车辆医生。{profile.name} 的当前灵魂指数为 {profile.soul_score}（{profile.soul_grade_label}）。",
        f"生命阶段: {profile.life_stage_label}，整体健康: {profile.health_score or 'N/A'}。",
    ]

    if profile.health_metrics:
        lines.append("各组件健康状态:")
        for m in profile.health_metrics[:5]:
            lines.append(f"  · {m.component}: {m.health_score} (风险: {m.risk_level})")

    if profile.predictions:
        lines.append("活跃预测:")
        for p in profile.predictions[:3]:
            lines.append(f"  · {p.prediction} (可信度: {p.confidence})")

    return "\n".join(lines)


def _maintenance_agent_response(profile: SoulProfile) -> str:
    """AI维修Agent — 维护建议."""
    b = profile.soul_breakdown
    lines = [
        f"我是您的AI维修顾问。{profile.name} 的维护质量评分为 {b.maintenance}。",
    ]

    if b.maintenance < 70:
        lines.append("维护质量偏低，建议尽快安排保养。")

    high_risk = [p for p in profile.predictions if p.risk_level in ("high", "critical")]
    if high_risk:
        lines.append(f"发现 {len(high_risk)} 个高风险预测，建议优先处理:")
        for p in high_risk[:3]:
            lines.append(f"  · {p.prediction}")
            if p.suggestion:
                lines.append(f"    建议: {p.suggestion}")

    return "\n".join(lines)


def _insurance_agent_response(profile: SoulProfile) -> str:
    """AI保险Agent — 风险评估."""
    b = profile.soul_breakdown
    lines = [
        f"我是您的AI保险顾问。{profile.name} 的风险评估如下:",
        f"  · 灵魂指数: {profile.soul_score} ({profile.soul_grade_label})",
        f"  · 健康状态: {b.health}",
        f"  · 驾驶安全: {b.driving}",
        f"  · 预测稳定性: {b.prediction}",
    ]

    if profile.soul_score >= 85:
        lines.append("车辆状况优秀，建议选择标准保费方案。")
    elif profile.soul_score >= 60:
        lines.append("车辆状况正常，建议选择增强保障方案。")
    else:
        lines.append("车辆存在风险，建议选择全面保障方案并安排检修。")

    return "\n".join(lines)
