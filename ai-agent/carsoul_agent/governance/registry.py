"""Enhanced Agent Registry — 智能体注册中心.

Implements §4 of the Governance Architecture: a central registry where
every agent is registered with rich metadata (capabilities, permissions,
version, lifecycle state) — not just a name→class mapping.

This supersedes the minimal ``agents/registry.py`` while keeping full
backward compatibility: the old ``register_agent`` / ``get_agent_class``
APIs still work, but now they also populate the managed registry.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent lifecycle states (§3.1 of Governance Architecture)."""

    ACTIVE = "ACTIVE"        # 空闲可用
    BUSY = "BUSY"            # 正在执行任务
    ERROR = "ERROR"          # 执行出错
    UPDATING = "UPDATING"    # 正在升级/配置
    OFFLINE = "OFFLINE"      # 离线不可用


@dataclass
class AgentMetadata:
    """Rich metadata for a registered agent (§4 data structure).

    Mirrors the JSON schema in the governance document:
    {
      "agent_id": "battery_agent",
      "name": "Battery Guardian",
      "role": "battery expert",
      "capabilities": ["SOH prediction", "thermal analysis", ...],
      "input_data": ["battery_temperature", "charging_history"],
      "permission": ["read_vehicle_battery"]
    }
    """

    agent_id: str
    name: str
    role: str
    capabilities: list[str] = field(default_factory=list)
    input_data: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    version: str = "v1.0"
    state: AgentState = AgentState.ACTIVE
    description: str = ""
    # Runtime stats (updated by the lifecycle manager).
    total_invocations: int = 0
    success_count: int = 0
    error_count: int = 0
    last_invoked: str | None = None
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a dict suitable for API responses."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "capabilities": self.capabilities,
            "input_data": self.input_data,
            "permissions": self.permissions,
            "version": self.version,
            "state": self.state.value,
            "description": self.description,
            "stats": {
                "total_invocations": self.total_invocations,
                "success_count": self.success_count,
                "error_count": self.error_count,
                "success_rate": (
                    self.success_count / self.total_invocations
                    if self.total_invocations > 0
                    else 0.0
                ),
                "last_invoked": self.last_invoked,
            },
            "registered_at": self.registered_at,
        }


class ManagedAgentRegistry:
    """Central registry with metadata, state management, and versioning.

    Extends the original ``AgentRegistry`` with:
      - Rich metadata per agent (capabilities, permissions, version)
      - Real-time state management (ACTIVE/BUSY/ERROR/OFFLINE)
      - Capability-based agent discovery
      - Runtime statistics tracking
    """

    def __init__(self) -> None:
        self._metadata: dict[str, AgentMetadata] = {}
        self._agent_classes: dict[str, type] = {}  # agent_id → class (optional)

    # ---- Registration ------------------------------------------------
    def register(
        self,
        agent_id: str,
        name: str,
        role: str,
        capabilities: list[str] | None = None,
        input_data: list[str] | None = None,
        permissions: list[str] | None = None,
        version: str = "v1.0",
        description: str = "",
        agent_class: type | None = None,
    ) -> AgentMetadata:
        """Register or update an agent's metadata."""
        meta = AgentMetadata(
            agent_id=agent_id,
            name=name,
            role=role,
            capabilities=capabilities or [],
            input_data=input_data or [],
            permissions=permissions or [],
            version=version,
            description=description,
        )
        self._metadata[agent_id] = meta
        if agent_class is not None:
            self._agent_classes[agent_id] = agent_class
        logger.info("Agent registered: %s (%s) v%s", agent_id, name, version)
        return meta

    def register_metadata(self, meta: AgentMetadata) -> None:
        """Register a pre-built AgentMetadata object."""
        self._metadata[meta.agent_id] = meta

    # ---- Lookup ------------------------------------------------------
    def get(self, agent_id: str) -> AgentMetadata | None:
        return self._metadata.get(agent_id)

    def get_class(self, agent_id: str) -> type | None:
        return self._agent_classes.get(agent_id)

    def all_metadata(self) -> list[AgentMetadata]:
        return list(self._metadata.values())

    def names(self) -> list[str]:
        return list(self._metadata.keys())

    # ---- State management (§3.1) ------------------------------------
    def update_state(self, agent_id: str, state: AgentState) -> bool:
        meta = self._metadata.get(agent_id)
        if meta is None:
            return False
        old = meta.state
        meta.state = state
        logger.debug("Agent %s state: %s → %s", agent_id, old.value, state.value)
        return True

    def list_by_state(self, state: AgentState) -> list[AgentMetadata]:
        return [m for m in self._metadata.values() if m.state == state]

    def list_active(self) -> list[AgentMetadata]:
        """All agents currently in ACTIVE state."""
        return self.list_by_state(AgentState.ACTIVE)

    # ---- Capability-based discovery (§5.3 Agent调度) ----------------
    def find_by_capability(self, capability: str) -> list[AgentMetadata]:
        """Find all agents that declare a given capability."""
        return [
            m for m in self._metadata.values()
            if capability in m.capabilities and m.state == AgentState.ACTIVE
        ]

    def find_by_role(self, role: str) -> list[AgentMetadata]:
        return [
            m for m in self._metadata.values()
            if m.role == role and m.state == AgentState.ACTIVE
        ]

    # ---- Stats (updated by lifecycle manager) -----------------------
    def record_invocation(self, agent_id: str, success: bool) -> None:
        meta = self._metadata.get(agent_id)
        if meta is None:
            return
        meta.total_invocations += 1
        meta.last_invoked = datetime.now(timezone.utc).isoformat()
        if success:
            meta.success_count += 1
        else:
            meta.error_count += 1

    # ---- Serialisation for API/frontend -----------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_count": len(self._metadata),
            "active_count": len(self.list_active()),
            "agents": [m.to_dict() for m in self._metadata.values()],
        }


# ------------------------------------------------------------------ #
#  Singleton instance
# ------------------------------------------------------------------ #
managed_registry = ManagedAgentRegistry()


def register_governance_agents() -> None:
    """Pre-register all CarSoul agents into the managed registry.

    Called once at startup to populate the registry with the five
    sub-agents, five expert agents, and the orchestrator — mirroring
    §6 of the Governance Architecture document.
    """
    # --- Orchestrator (§5) ---
    managed_registry.register(
        agent_id="carsoul_guardian",
        name="CarSoul Guardian",
        role="orchestrator",
        capabilities=[
            "intent_understanding",
            "task_decomposition",
            "agent_scheduling",
            "result_fusion",
        ],
        input_data=["user_message", "vehicle_state"],
        permissions=[
            "read_vehicle_all",
            "write_digital_twin",
            "invoke_all_agents",
        ],
        version="v1.0",
        description="车辆生命总调度Agent — 负责意图理解、任务拆解、Agent调度与结果融合。",
    )

    # --- Core sub-agents (§6.1–6.6 mapped to workflow nodes) ---
    managed_registry.register(
        agent_id="perception",
        name="Perception Agent",
        role="perception",
        capabilities=["anomaly_detection", "threshold_analysis", "semantic_detection"],
        input_data=["sensor_window", "vehicle_state"],
        permissions=["read_vehicle_sensors", "read_vehicle_health"],
        version="v1.0",
        description="状态感知Agent — 读取传感器窗口，做阈值+语义异常检测。",
    )

    managed_registry.register(
        agent_id="diagnosis",
        name="Diagnosis Agent",
        role="diagnosis",
        capabilities=["expert_consultation", "root_cause_analysis", "knowledge_matching"],
        input_data=["anomalies", "vehicle_state", "knowledge_context"],
        permissions=["read_vehicle_all", "read_knowledge_base"],
        version="v1.0",
        description="故障诊断Agent — 召集五专科专家并行会诊，汇总统一诊断结论。",
    )

    managed_registry.register(
        agent_id="risk",
        name="Risk Agent",
        role="risk_assessment",
        capabilities=["risk_quantification", "probability_estimation", "eta_prediction"],
        input_data=["diagnosis", "trip_context", "calibration_context"],
        permissions=["read_vehicle_all", "read_risk_history"],
        version="v1.0",
        description="风险评估Agent — 量化风险等级、发生概率与预计剩余可用时间。",
    )

    managed_registry.register(
        agent_id="explainer",
        name="Explainer Agent",
        role="explanation",
        capabilities=["natural_language_generation", "report_formatting", "trip_report"],
        input_data=["diagnosis", "risk_assessment", "driver_profile"],
        permissions=["read_vehicle_all"],
        version="v1.0",
        description="解释生成Agent — 将诊断结果转化为用户可理解的语言与结构化报告。",
    )

    managed_registry.register(
        agent_id="service",
        name="Service Agent",
        role="service_suggestion",
        capabilities=["action_recommendation", "reminder_generation", "escalation"],
        input_data=["diagnosis", "risk_assessment"],
        permissions=["read_vehicle_all", "write_digital_twin", "send_reminder"],
        version="v1.0",
        description="服务建议Agent — 生成行动建议、推送提醒、记录至车辆数字生命档案。",
    )

    # --- Expert panel (§6 specialist agents) ---
    expert_specs = [
        ("powertrain_expert", "Powertrain Expert", "动力系统专家",
         ["battery_analysis", "engine_analysis", "thermal_risk"],
         ["battery_temperature", "soc", "engine_temp"],
         ["read_vehicle_battery", "read_vehicle_engine"]),
        ("chassis_expert", "Chassis Expert", "底盘系统专家",
         ["brake_analysis", "tire_analysis", "suspension_check"],
         ["brake_pad_remaining_km", "tire_tread_mm"],
         ["read_vehicle_brake", "read_vehicle_tire"]),
        ("electrical_expert", "Electrical Expert", "电气系统专家",
         ["sensor_diagnosis", "circuit_check", "fault_code_analysis"],
         ["sensor_readings", "fault_codes"],
         ["read_vehicle_sensors", "read_fault_codes"]),
        ("driving_expert", "Driving Behavior Expert", "驾驶行为专家",
         ["driving_pattern_analysis", "safety_assessment", "energy_consumption"],
         ["driving_behavior", "safety_score"],
         ["read_driving_behavior"]),
        ("maintenance_expert", "Maintenance Expert", "保养规划专家",
         ["maintenance_prediction", "cost_estimation", "schedule_optimization"],
         ["mileage", "health_score", "maintenance_history"],
         ["read_vehicle_all", "read_maintenance_history"]),
    ]
    for eid, ename, cn_name, caps, inputs, perms in expert_specs:
        managed_registry.register(
            agent_id=eid,
            name=ename,
            role=cn_name,
            capabilities=caps,
            input_data=inputs,
            permissions=perms,
            version="v1.0",
            description=f"{cn_name} — 负责相关领域的专业会诊。",
        )

    # --- Extended domain experts (§6.5–6.10 of Agent Team Design) ---
    extended_specs = [
        ("value_expert", "Vehicle Value Agent", "车辆价值专家",
         ["vehicle_valuation", "depreciation_forecast", "resale_analysis"],
         ["mileage", "health_score", "purchase_price", "energy_type"],
         ["read_vehicle_all"]),
        ("environment_expert", "Environment Adaptation Agent", "环境适应专家",
         ["environment_impact_analysis", "weather_adaptation", "temperature_analysis"],
         ["sensor_readings", "weather_data", "trip_context"],
         ["read_vehicle_sensors"]),
        ("charging_expert", "Charging Intelligence Agent", "充电智能专家",
         ["charging_strategy_optimization", "charging_station_recommendation", "charging_behavior_analysis"],
         ["soc_history", "charging_pattern", "battery_temperature"],
         ["read_vehicle_battery"]),
        ("energy_expert", "Energy Optimization Agent", "能耗优化专家",
         ["energy_consumption_analysis", "range_optimization", "efficiency_improvement"],
         ["driving_behavior", "eco_score", "energy_consumption"],
         ["read_driving_behavior", "read_vehicle_all"]),
        ("companion_expert", "User Companion Agent", "用户陪伴专家",
         ["user_preference_analysis", "personalized_recommendation", "lifecycle_companion"],
         ["driving_profile", "user_preferences", "historical_interactions"],
         ["read_driving_behavior"]),
    ]
    for eid, ename, cn_name, caps, inputs, perms in extended_specs:
        managed_registry.register(
            agent_id=eid,
            name=ename,
            role=cn_name,
            capabilities=caps,
            input_data=inputs,
            permissions=perms,
            version="v1.0",
            description=f"{cn_name} — 负责相关领域的专业会诊。",
        )

    # --- Judge Agent (§10 冲突治理) ---
    managed_registry.register(
        agent_id="judge",
        name="Judge Agent",
        role="conflict_resolution",
        capabilities=["conflict_detection", "confidence_weighting", "decision_fusion"],
        input_data=["expert_opinions", "diagnosis"],
        permissions=["read_all_agent_outputs"],
        version="v1.0",
        description="决策裁判Agent — 当多专家意见冲突时，基于数据可信度、历史准确率、模型评分仲裁。",
    )

    logger.info("Governance registry initialised with %d agents", len(managed_registry.names()))
