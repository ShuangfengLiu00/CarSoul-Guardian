"""Vehicle digital-life record schemas (TASK007 core).

This module defines the two flagship read models of the digital-twin engine:

* ``VehicleLifeRecord`` — the narrative "digital life" view returned by
  ``GET /api/vehicle/{id}/life``. It distils the full archive into the
  human/agent-facing summary shown on the *Vehicle Digital Life Home* page:
  identity, age, health index, mileage, predicted lifespan, life-event
  timeline, AI suggestions, and prediction list.

* ``VehicleHealthScore`` — the Vehicle Health Score (VHS) computed by the
  weighted model::

      VHS = 0.30·Engine + 0.25·Battery + 0.15·Chassis
            + 0.15·Driving + 0.15·Maintenance

  graded into 黄金车况 / 优秀 / 一般 / 风险车辆.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Vehicle Health Score (VHS)
# ---------------------------------------------------------------------------

class HealthScoreBreakdown(BaseModel):
    """Per-component contribution to the overall VHS."""
    engine: float = Field(0.0, description="发动机分(0-100)")
    battery: float = Field(0.0, description="电池/电力分(0-100)")
    chassis: float = Field(0.0, description="底盘(制动+轮胎+车身)分(0-100)")
    driving: float = Field(0.0, description="驾驶习惯分(0-100)")
    maintenance: float = Field(0.0, description="维修记录分(0-100)")

    # Weighted contributions (component × weight)
    engine_contribution: float = 0.0
    battery_contribution: float = 0.0
    chassis_contribution: float = 0.0
    driving_contribution: float = 0.0
    maintenance_contribution: float = 0.0


class VehicleHealthScore(BaseModel):
    """The computed Vehicle Health Score (VHS)."""
    vehicle_id: int
    score: float = Field(..., ge=0, le=100, description="综合健康分数")
    grade: str = Field(..., description="评级: golden|excellent|fair|risk")
    grade_label: str = Field(..., description="评级中文: 黄金车况|优秀|一般|风险车辆")
    breakdown: HealthScoreBreakdown
    weights: dict[str, float] = Field(
        default_factory=lambda: {
            "engine": 0.30,
            "battery": 0.25,
            "chassis": 0.15,
            "driving": 0.15,
            "maintenance": 0.15,
        }
    )
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Vehicle Digital Life Record
# ---------------------------------------------------------------------------

class LifeEventItem(BaseModel):
    """A milestone on the vehicle life timeline."""
    date: date | datetime
    event_type: str
    title: str
    description: str | None = None
    mileage: int | None = None
    cost: float | None = None
    icon: str | None = None  # frontend icon hint


class PredictionItem(BaseModel):
    """A forward-looking AI prediction / suggestion."""
    component: str
    current_health: float | None = None
    predicted_failure_date: date | None = None
    risk_level: str  # low | medium | high
    reason: str
    suggestion: str | None = None


class VehicleIdentity(BaseModel):
    """The vehicle's digital identity card."""
    vehicle_id: int
    digital_identity: str = Field(..., description="数字身份号 VX-YYYY-NNNNN")
    name: str
    brand: str
    model: str
    year: int
    vin: str
    energy_type: str
    color: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None


class VehicleLifeRecord(BaseModel):
    """The complete digital-life record — the soul of the digital twin."""
    model_config = ConfigDict(from_attributes=True)

    identity: VehicleIdentity

    # ---- Vitals ----
    health_score: int | None = Field(None, ge=0, le=100)
    health_grade: str | None = None
    health_grade_label: str | None = None
    status: str = Field("GOOD", description="GOOD|WARNING|DANGER|END_OF_LIFE")
    status_label: str = "健康"

    # ---- Age / usage ----
    age_years: float = 0.0
    age_label: str = "新车"
    mileage: int = 0
    mileage_label: str = "0 km"

    # ---- Predicted remaining life ----
    predicted_lifespan_years: float | None = None
    predicted_remaining_years: float | None = None
    predicted_lifespan_label: str | None = None

    # ---- Today's snapshot ----
    today_temperature: float | None = None
    today_fuel_level: float | None = None
    today_location: dict[str, Any] | None = None

    # ---- Sub-system health (from digital state) ----
    engine_health: float | None = None
    battery_health: float | None = None
    brake_health: float | None = None
    tire_health: float | None = None

    # ---- VHS breakdown ----
    health_breakdown: HealthScoreBreakdown | None = None

    # ---- Narrative sections ----
    life_events: list[LifeEventItem] = Field(default_factory=list)
    predictions: list[PredictionItem] = Field(default_factory=list)
    ai_suggestions: list[str] = Field(default_factory=list)

    # ---- Stats ----
    total_trips: int = 0
    total_maintenance_cost: float = 0.0
    fault_count: int = 0
    active_fault_count: int = 0

    # ---- AI extension hooks (reserved for TASK008) ----
    ai_doctor_enabled: bool = False
    personality: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Mock data generator request
# ---------------------------------------------------------------------------

class SimulationRequest(BaseModel):
    """Request body for the mock-data generator / simulator."""
    vehicle_id: int
    sensor_points: int = Field(24, ge=1, le=500, description="生成传感器数据点数")
    trip_count: int = Field(5, ge=0, le=50, description="生成行程数")
    fault_count: int = Field(0, ge=0, le=10, description="生成故障数")
    days: int = Field(7, ge=1, le=90, description="数据时间跨度(天)")
    update_digital_state: bool = Field(True, description="是否刷新实时数字状态")


class SimulationResult(BaseModel):
    """Result of a mock-data generation run."""
    vehicle_id: int
    sensor_data_created: int = 0
    trips_created: int = 0
    faults_created: int = 0
    digital_state_updated: bool = False
    message: str = ""
