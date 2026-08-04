"""Digital Life Engine schemas — TASK007-V2.

Pydantic models for the Vehicle Digital Life Engine API:
  - Vehicle Identity (数字身份)
  - Vehicle Life State (生命状态)
  - Vehicle Health Metrics (细分健康)
  - Vehicle Sensor Stream (传感器时间序列)
  - Vehicle Life Event (生命事件 ⭐)
  - Vehicle Memory (记忆系统 ⭐)
  - Driver Profile (驾驶人格)
  - Vehicle Prediction (AI预测)
  - Vehicle Soul Score (VSS 灵魂指数)
  - Soul Profile (灵魂档案聚合视图)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ===========================================================================
# 1. Vehicle Identity (数字身份)
# ===========================================================================

class VehicleIdentityCreate(BaseModel):
    brand: str = Field(..., description="品牌")
    model: str = Field(..., description="车型")
    production_year: int | None = None
    energy_type: str = Field("electric", description="electric | gasoline | hybrid | ...")
    vehicle_class: str | None = Field(None, description="SUV | sedan | hatchback | ...")
    vin: str | None = None
    owner_id: int | None = None
    nickname: str | None = None


class VehicleIdentityOut(BaseModel):
    id: int
    vehicle_id: int
    vehicle_uuid: str = Field(..., description="灵魂ID CSG-YYYY-NNNNN")
    vin: str | None = None
    brand: str | None = None
    model: str | None = None
    production_year: int | None = None
    energy_type: str | None = None
    vehicle_class: str | None = None
    owner_id: int | None = None
    birth_time: datetime | None = None
    nickname: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# 2. Vehicle Life State (生命状态)
# ===========================================================================

class VehicleLifeStateOut(BaseModel):
    id: int
    vehicle_id: int
    health_score: float | None = None
    life_stage: str = Field("NEW", description="NEW | GROWTH | MATURE | AGING | RETIRE")
    mileage: int = 0
    vehicle_age_days: int = 0
    energy_health: float | None = None
    mechanical_health: float | None = None
    software_health: float | None = None
    soul_score: float | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# 3. Vehicle Health Metrics (细分健康)
# ===========================================================================

class VehicleHealthMetricsCreate(BaseModel):
    component: str = Field(..., description="battery | motor | brake | tire | body | electronics | cooling")
    health_score: float | None = None
    temperature: float | None = None
    wear_level: float | None = None
    risk_level: str = "low"


class VehicleHealthMetricsOut(VehicleHealthMetricsCreate):
    id: int
    vehicle_id: int
    record_time: datetime

    model_config = {"from_attributes": True}


class VehicleHealthMetricsList(BaseModel):
    items: list[VehicleHealthMetricsOut]
    total: int


# ===========================================================================
# 4. Vehicle Sensor Stream (传感器时间序列)
# ===========================================================================

class VehicleSensorStreamCreate(BaseModel):
    sensor_name: str
    value: float
    unit: str | None = None
    meta: dict[str, Any] | None = None


class VehicleSensorStreamOut(VehicleSensorStreamCreate):
    id: int
    vehicle_id: int
    timestamp: datetime

    model_config = {"from_attributes": True}


class VehicleSensorStreamList(BaseModel):
    items: list[VehicleSensorStreamOut]
    total: int


# ===========================================================================
# 5. Vehicle Life Event (生命事件 ⭐)
# ===========================================================================

class VehicleLifeEventCreate(BaseModel):
    event_type: str = Field(..., description="PURCHASE | FIRST_DRIVE | TRAVEL | MAINTENANCE | ACCIDENT | WARNING | RECOVERY | UPGRADE | CUSTOM")
    title: str
    description: str | None = None
    importance: int = Field(5, ge=1, le=10, description="1-10, 10=最重要")
    mileage: int | None = None
    location: str | None = None
    cost: float | None = None
    extra_data: dict[str, Any] | None = None
    event_time: datetime | None = None


class VehicleLifeEventOut(VehicleLifeEventCreate):
    id: int
    vehicle_id: int
    event_time: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class VehicleLifeEventList(BaseModel):
    items: list[VehicleLifeEventOut]
    total: int


# ===========================================================================
# 6. Vehicle Memory (记忆系统 ⭐)
# ===========================================================================

class VehicleMemoryCreate(BaseModel):
    memory_type: str = Field(..., description="habit | event | preference | warning | recovery | emotion | context")
    content: str
    emotion_score: float | None = Field(None, ge=-1.0, le=1.0, description="-1.0 to 1.0")
    importance: int = Field(5, ge=1, le=10)
    source: str = "system"
    meta_data: dict[str, Any] | None = None


class VehicleMemoryOut(VehicleMemoryCreate):
    id: int
    vehicle_id: int
    created_time: datetime

    model_config = {"from_attributes": True}


class VehicleMemoryList(BaseModel):
    items: list[VehicleMemoryOut]
    total: int


# ===========================================================================
# 7. Driver Profile (驾驶人格)
# ===========================================================================

class DriverProfileOut(BaseModel):
    id: int
    vehicle_id: int
    driver_style: str = "balanced"
    aggressive_score: float | None = None
    comfort_score: float | None = None
    eco_score: float | None = None
    total_trips: int = 0
    total_distance: float = 0
    total_duration: int = 0
    total_harsh_events: int = 0
    preferred_speed_range: str | None = None
    preferred_driving_time: str | None = None
    preferred_road_type: str | None = None
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===========================================================================
# 8. Vehicle Prediction (AI预测)
# ===========================================================================

class VehiclePredictionCreate(BaseModel):
    target_component: str = Field(..., description="battery | brake | tire | motor | ...")
    prediction: str
    risk_level: str = "low"
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    predicted_value: float | None = None
    predicted_unit: str | None = None
    predicted_time: datetime | None = None
    root_cause: str | None = None
    suggestion: str | None = None


class VehiclePredictionOut(VehiclePredictionCreate):
    id: int
    vehicle_id: int
    status: str = "active"
    actual_outcome: str | None = None
    prediction_time: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class VehiclePredictionList(BaseModel):
    items: list[VehiclePredictionOut]
    total: int


# ===========================================================================
# 9. Vehicle Soul Score (VSS 灵魂指数)
# ===========================================================================

class SoulScoreBreakdown(BaseModel):
    health: float = Field(..., description="健康状态 0-100, 权重40%")
    memory: float = Field(..., description="记忆丰富度 0-100, 权重15%")
    maintenance: float = Field(..., description="维护质量 0-100, 权重15%")
    driving: float = Field(..., description="驾驶关系 0-100, 权重15%")
    prediction: float = Field(..., description="预测稳定性 0-100, 权重15%")

    health_contribution: float = 0.0
    memory_contribution: float = 0.0
    maintenance_contribution: float = 0.0
    driving_contribution: float = 0.0
    prediction_contribution: float = 0.0


class VehicleSoulScore(BaseModel):
    vehicle_id: int
    soul_id: str
    score: float = Field(..., description="VSS 0-100")
    grade: str = Field(..., description="legendary | excellent | normal | risk")
    grade_label: str
    breakdown: SoulScoreBreakdown
    computed_at: datetime


class VehicleSoulScoreHistoryOut(BaseModel):
    id: int
    vehicle_id: int
    soul_score: float
    health_score: float | None = None
    memory_score: float | None = None
    maintenance_score: float | None = None
    driving_score: float | None = None
    prediction_score: float | None = None
    grade: str | None = None
    notes: str | None = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class VehicleSoulScoreHistoryList(BaseModel):
    items: list[VehicleSoulScoreHistoryOut]
    total: int


# ===========================================================================
# 10. Soul Profile (灵魂档案聚合视图) — 旗舰读模型
# ===========================================================================

class SoulProfile(BaseModel):
    """车辆数字生命灵魂档案 — 聚合所有数字生命数据的旗舰读模型."""

    # Identity
    soul_id: str = Field(..., description="灵魂ID CSG-YYYY-NNNNN")
    vehicle_id: int
    name: str
    brand: str
    model: str
    year: int | None = None
    energy_type: str
    nickname: str | None = None

    # Soul Score
    soul_score: float = Field(..., description="VSS 0-100")
    soul_grade: str
    soul_grade_label: str
    soul_breakdown: SoulScoreBreakdown

    # Life State
    life_stage: str = Field("NEW", description="NEW | GROWTH | MATURE | AGING | RETIRE")
    life_stage_label: str
    health_score: float | None = None
    energy_health: float | None = None
    mechanical_health: float | None = None
    software_health: float | None = None

    # Companion stats
    companion_days: int = 0
    mileage: int = 0
    mileage_label: str = "0 km"

    # Life events
    life_events: list[VehicleLifeEventOut] = []
    life_events_count: int = 0

    # Memories
    memories: list[VehicleMemoryOut] = []
    memories_count: int = 0

    # Health metrics
    health_metrics: list[VehicleHealthMetricsOut] = []

    # Predictions
    predictions: list[VehiclePredictionOut] = []

    # Driver profile
    driver_profile: DriverProfileOut | None = None
    driver_style_label: str = "未知"

    # AI insights
    ai_insights: list[str] = []

    # Agent hooks (future)
    agent_hooks: dict[str, Any] = Field(
        default_factory=lambda: {
            "ai_doctor": {"status": "available", "endpoint": "/api/digital-twin/{id}/agent/doctor"},
            "ai_maintenance": {"status": "available", "endpoint": "/api/digital-twin/{id}/agent/maintenance"},
            "ai_insurance": {"status": "available", "endpoint": "/api/digital-twin/{id}/agent/insurance"},
        }
    )


# ===========================================================================
# Create Digital Life Response
# ===========================================================================

class CreateDigitalLifeResponse(BaseModel):
    """POST /api/digital-twin/create response."""

    vehicle_id: int
    soul_id: str
    message: str
    identity: VehicleIdentityOut


# ===========================================================================
# Agent Interface Schema (future hooks)
# ===========================================================================

class AgentQueryRequest(BaseModel):
    """AI Agent 查询请求 — 统一接口给三种 Agent."""

    query: str = Field(..., description="用户问题或查询指令")
    agent_type: str = Field("doctor", description="doctor | maintenance | insurance")
    context: dict[str, Any] | None = None


class AgentQueryResponse(BaseModel):
    """AI Agent 查询响应."""

    agent_type: str
    answer: str
    confidence: float | None = None
    suggestions: list[str] = []
    data: dict[str, Any] | None = None
