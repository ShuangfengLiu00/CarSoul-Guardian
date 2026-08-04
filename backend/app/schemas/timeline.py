"""Timeline Demo API schemas — 'A Car's Life' narrative endpoint.

Defines the response model for GET /api/timeline/life-story, which tells
the 3-year story of a virtual vehicle from birth to anomaly detection,
including memory entries, agent collaboration, and a traceable health report.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


# ------------------------------------------------------------------ #
#  Telemetry & Memory
# ------------------------------------------------------------------ #
class TelemetrySnapshot(BaseModel):
    """A point-in-time telemetry snapshot for one phase."""
    day: int
    mileage: float
    soh: float  # State of Health, 0-100
    battery_temp: float
    charging_speed_ratio: float  # 1.0 = normal, <1.0 = degraded
    charge_cycles: int
    fast_charge_ratio: float  # 0-1, proportion of fast charging


class MemoryEntry(BaseModel):
    """A memory-engine entry associated with a timeline phase."""
    id: str
    event_type: str  # habit / event / warning / recovery / anomaly
    summary: str
    impact_target: str | None = None
    impact_delta: float = 0.0
    occurred_at: str  # ISO date
    source: str = "simulator"


class TimelineEvent(BaseModel):
    """A key milestone event in the vehicle's life."""
    day: int
    date: str
    title: str
    description: str
    event_type: str  # birth / mileage / maintenance / warning / anomaly / milestone
    mileage: float | None = None


# ------------------------------------------------------------------ #
#  Agent Collaboration
# ------------------------------------------------------------------ #
class AgentFinding(BaseModel):
    """One agent's diagnostic finding during anomaly collaboration."""
    agent_name: str  # battery / diagnosis / safety / value
    skill_name: str
    severity: str  # info / warning / critical
    finding: str
    recommendation: str
    confidence: float


class AgentCollaboration(BaseModel):
    """Guardian-convened multi-agent diagnostic session."""
    triggered: bool
    trigger_reason: str | None = None
    guardian_summary: str | None = None
    findings: list[AgentFinding] = Field(default_factory=list)


# ------------------------------------------------------------------ #
#  Timeline Phase
# ------------------------------------------------------------------ #
class TimelinePhase(BaseModel):
    """One year/phase in the vehicle's life story."""
    year: int
    label: str  # 诞生 / 用车 / 异常
    summary: str
    color: str  # hex color for UI
    telemetry: TelemetrySnapshot
    events: list[TimelineEvent] = Field(default_factory=list)
    memories: list[MemoryEntry] = Field(default_factory=list)
    agent_collaboration: AgentCollaboration | None = None


# ------------------------------------------------------------------ #
#  Health Report (Final)
# ------------------------------------------------------------------ #
class TraceableItem(BaseModel):
    """A report metric that can be traced back to source data."""
    label: str
    value: str
    source_type: str  # memory / telemetry / agent
    source_id: str
    source_description: str


class UsedCarValuation(BaseModel):
    current: float  # 当前估值 (万元)
    projected: float  # 优化后预计 (万元)
    delta: float  # 提升空间 (万元)


class HealthReport(BaseModel):
    """Final report card — every number is traceable."""
    health_score: int
    health_grade: str  # 优秀 / 良好 / 一般 / 风险
    battery_degradation_12m: float  # 未来12个月电池衰减百分比
    charging_strategy: str
    used_car_valuation: UsedCarValuation
    traceable_items: list[TraceableItem] = Field(default_factory=list)


# ------------------------------------------------------------------ #
#  Top-level Response
# ------------------------------------------------------------------ #
class VehicleInfo(BaseModel):
    vin: str
    name: str
    profile: str  # family_ev / performance_ev / hybrid
    brand: str
    model: str


class LifeStoryResponse(BaseModel):
    """Complete 'A Car's Life' narrative response."""
    vehicle: VehicleInfo
    phases: list[TimelinePhase]
    report: HealthReport
    demo_mode: bool = True  # 红线2合规: always true for simulated data
