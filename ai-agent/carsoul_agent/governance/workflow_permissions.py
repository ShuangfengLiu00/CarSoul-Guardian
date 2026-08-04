"""Workflow Permission Checker — 工作流级权限控制 (§9 Workflow Layer).

Extends the agent-level permission model (``permissions.py``) with
*workflow-level* access control. While ``permissions.py`` governs
"which agent may access which data", this module governs "which agents,
skills, and data resources may participate in a given workflow".

A *workflow* is a multi-step business process such as:

    long_trip_check          — 出行前检查
    energy_anomaly_analysis  — 能耗异常分析
    battery_thermal_risk     — 电池热风险评估
    fault_diagnosis          — 故障诊断
    maintenance_planning     — 保养规划
    health_assessment        — 健康评估
    knowledge_query          — 知识查询

Each workflow declares:
  - ``allowed_agents``   — the agents that may be scheduled within it.
  - ``allowed_skills``   — the skills that may be invoked within it.
  - ``allowed_data``     — the data resources that may be read.
  - ``risk_level``       — low / medium / high / critical.
  - ``requires_human_approval`` — whether a human must approve before
    the workflow may execute (e.g. battery_thermal_risk).

This mirrors the pattern used by ``registry.py`` and ``permissions.py``:
a dataclass plus a central checker with lookup helpers and a singleton
instance seeded by ``register_workflow_permissions()``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Sentinel meaning "all agents / all skills / all data are allowed".
_WILDCARD = "*"


@dataclass
class WorkflowPermission:
    """Permission policy for a single workflow (§9 workflow scope).

    Mirrors the workflow permission schema:

        {
          "workflow_name": "long_trip_check",
          "allowed_agents": ["*"],
          "allowed_skills": ["range_prediction", "vehicle_risk_detection"],
          "allowed_data": ["vehicle.battery.read", "vehicle.tire.read"],
          "risk_level": "high",
          "requires_human_approval": false
        }
    """

    workflow_name: str
    allowed_agents: list[str] = field(default_factory=list)
    allowed_skills: list[str] = field(default_factory=list)
    allowed_data: list[str] = field(default_factory=list)
    risk_level: str = "low"  # low / medium / high / critical.
    requires_human_approval: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a dict suitable for API responses."""
        return {
            "workflow_name": self.workflow_name,
            "allowed_agents": self.allowed_agents,
            "allowed_skills": self.allowed_skills,
            "allowed_data": self.allowed_data,
            "risk_level": self.risk_level,
            "requires_human_approval": self.requires_human_approval,
            "description": self.description,
        }


class WorkflowPermissionChecker:
    """Enforces workflow-level access control at runtime.

    Usage:

        if workflow_permission_checker.check_agent("long_trip_check", "battery_agent"):
            # agent may participate in this workflow
        if workflow_permission_checker.check_skill("long_trip_check", "range_prediction"):
            # skill may be invoked within this workflow
    """

    def __init__(self) -> None:
        self._permissions: dict[str, WorkflowPermission] = {}

    # ---- Registration ------------------------------------------------
    def register(
        self,
        workflow_name: str,
        allowed_agents: list[str] | None = None,
        allowed_skills: list[str] | None = None,
        allowed_data: list[str] | None = None,
        risk_level: str = "low",
        requires_human_approval: bool = False,
        description: str = "",
    ) -> WorkflowPermission:
        """Register or update a workflow permission policy."""
        perm = WorkflowPermission(
            workflow_name=workflow_name,
            allowed_agents=allowed_agents or [],
            allowed_skills=allowed_skills or [],
            allowed_data=allowed_data or [],
            risk_level=risk_level,
            requires_human_approval=requires_human_approval,
            description=description,
        )
        self._permissions[workflow_name] = perm
        logger.info(
            "Workflow permission registered: %s (risk=%s, approval=%s)",
            workflow_name, risk_level, requires_human_approval,
        )
        return perm

    # ---- Lookup ------------------------------------------------------
    def get(self, workflow_name: str) -> WorkflowPermission | None:
        """Return the workflow permission, or None if not found."""
        return self._permissions.get(workflow_name)

    def all_permissions(self) -> list[WorkflowPermission]:
        """Return all registered workflow permissions."""
        return list(self._permissions.values())

    def names(self) -> list[str]:
        """Return all registered workflow names."""
        return list(self._permissions.keys())

    # ---- Checks ------------------------------------------------------
    def check_agent(self, workflow_name: str, agent_id: str) -> bool:
        """Return True if *agent_id* may participate in *workflow_name*."""
        perm = self._permissions.get(workflow_name)
        if perm is None:
            logger.warning("Unknown workflow: %s", workflow_name)
            return False
        if _WILDCARD in perm.allowed_agents:
            return True
        return agent_id in perm.allowed_agents

    def check_skill(self, workflow_name: str, skill_id: str) -> bool:
        """Return True if *skill_id* may be invoked within *workflow_name*."""
        perm = self._permissions.get(workflow_name)
        if perm is None:
            logger.warning("Unknown workflow: %s", workflow_name)
            return False
        if _WILDCARD in perm.allowed_skills:
            return True
        return skill_id in perm.allowed_skills

    def check_data(self, workflow_name: str, data_resource: str) -> bool:
        """Return True if *data_resource* may be read within *workflow_name*.

        ``data_resource`` may be an MCP interface id (e.g.
        ``vehicle.battery.read``) or a logical data name (e.g.
        ``battery_temperature``).
        """
        perm = self._permissions.get(workflow_name)
        if perm is None:
            logger.warning("Unknown workflow: %s", workflow_name)
            return False
        if _WILDCARD in perm.allowed_data:
            return True
        return data_resource in perm.allowed_data

    def requires_approval(self, workflow_name: str) -> bool:
        """Return True if *workflow_name* requires human approval."""
        perm = self._permissions.get(workflow_name)
        if perm is None:
            return True  # Unknown workflows default to requiring approval.
        return perm.requires_human_approval

    # ---- Serialisation for API/frontend -----------------------------
    def to_dict(self) -> dict[str, Any]:
        """Serialise the entire checker for API/frontend."""
        return {
            "workflow_count": len(self._permissions),
            "workflows": [p.to_dict() for p in self._permissions.values()],
        }


# ------------------------------------------------------------------ #
#  Singleton instance
# ------------------------------------------------------------------ #
workflow_permission_checker = WorkflowPermissionChecker()


def register_workflow_permissions() -> None:
    """Pre-register all CarSoul workflow permission policies.

    Called once at startup to populate the checker with ~7 workflows
    covering the main business processes defined in the governance
    architecture.
    """

    # --- long_trip_check: 出行前检查 ---
    # Allows all agents; risk level high because it gates real-world travel.
    workflow_permission_checker.register(
        workflow_name="long_trip_check",
        allowed_agents=[_WILDCARD],
        allowed_skills=[
            "battery_health_analysis",
            "range_prediction",
            "vehicle_risk_detection",
            "brake_analysis",
            "tire_analysis",
            "safety_assessment",
            "health_score_computation",
            "trip_report_generation",
        ],
        allowed_data=[
            "vehicle.battery.read",
            "vehicle.brake.read",
            "vehicle.tire.read",
            "vehicle.health.query",
            "vehicle.driving_behavior.read",
        ],
        risk_level="high",
        requires_human_approval=False,
        description="出行前全面检查工作流 — 评估车辆状态是否适合长途出行。",
    )

    # --- energy_anomaly_analysis: 能耗异常分析 ---
    workflow_permission_checker.register(
        workflow_name="energy_anomaly_analysis",
        allowed_agents=[
            "powertrain_expert",
            "driving_expert",
            "perception",
            "diagnosis",
        ],
        allowed_skills=[
            "energy_consumption_analysis",
            "battery_health_analysis",
            "driving_pattern_analysis",
            "anomaly_detection",
            "fault_diagnosis",
        ],
        allowed_data=[
            "vehicle.battery.read",
            "vehicle.driving_behavior.read",
            "vehicle.sensor.read",
        ],
        risk_level="medium",
        requires_human_approval=False,
        description="能耗异常分析工作流 — 定位能耗偏高的根因。",
    )

    # --- battery_thermal_risk: 电池热风险评估 ---
    # High-risk and requires human approval before executing.
    workflow_permission_checker.register(
        workflow_name="battery_thermal_risk",
        allowed_agents=[
            "powertrain_expert",
            "risk",
        ],
        allowed_skills=[
            "thermal_risk_assessment",
            "battery_failure_prediction",
            "vehicle_risk_detection",
            "risk_quantification",
        ],
        allowed_data=[
            "vehicle.battery.read",
            "vehicle.sensor.read",
            "vehicle.risk.predict",
        ],
        risk_level="critical",
        requires_human_approval=True,
        description="电池热风险评估工作流 — 评估热失控风险，需人工确认后方可执行。",
    )

    # --- fault_diagnosis: 故障诊断 ---
    workflow_permission_checker.register(
        workflow_name="fault_diagnosis",
        allowed_agents=[
            "diagnosis",
            "electrical_expert",
            "powertrain_expert",
            "chassis_expert",
            "maintenance_expert",
            "judge",
        ],
        allowed_skills=[
            "fault_diagnosis",
            "sensor_diagnosis",
            "fault_code_analysis",
            "battery_health_analysis",
            "brake_analysis",
            "tire_analysis",
            "conflict_resolution",
        ],
        allowed_data=[
            "vehicle.sensor.read",
            "vehicle.fault.query",
            "vehicle.battery.read",
            "vehicle.brake.read",
            "vehicle.tire.read",
            "knowledge.search",
        ],
        risk_level="medium",
        requires_human_approval=False,
        description="故障诊断工作流 — 多专家会诊定位故障根因。",
    )

    # --- maintenance_planning: 保养规划 ---
    workflow_permission_checker.register(
        workflow_name="maintenance_planning",
        allowed_agents=[
            "maintenance_expert",
            "service",
        ],
        allowed_skills=[
            "maintenance_prediction",
            "cost_estimation",
            "vehicle_valuation",
            "depreciation_forecast",
            "reminder_generation",
            "personalized_recommendation",
        ],
        allowed_data=[
            "vehicle.maintenance.search",
            "vehicle.health.query",
            "vehicle.lifecycle.events",
        ],
        risk_level="low",
        requires_human_approval=False,
        description="保养规划工作流 — 预测保养时间、估算费用并生成提醒。",
    )

    # --- health_assessment: 健康评估 ---
    workflow_permission_checker.register(
        workflow_name="health_assessment",
        allowed_agents=[_WILDCARD],
        allowed_skills=[
            "health_score_computation",
            "battery_health_analysis",
            "brake_analysis",
            "tire_analysis",
            "safety_assessment",
            "lifecycle_prediction",
        ],
        allowed_data=[_WILDCARD],
        risk_level="low",
        requires_human_approval=False,
        description="车辆健康评估工作流 — 综合各子系统健康数据计算整体评分。",
    )

    # --- knowledge_query: 知识查询 ---
    workflow_permission_checker.register(
        workflow_name="knowledge_query",
        allowed_agents=["diagnosis"],
        allowed_skills=[
            "knowledge_qa",
            "technical_explanation",
        ],
        allowed_data=[
            "knowledge.search",
        ],
        risk_level="low",
        requires_human_approval=False,
        description="知识查询工作流 — 基于车辆知识库回答用户问题。",
    )

    logger.info(
        "Workflow permissions initialised with %d workflows",
        len(workflow_permission_checker.names()),
    )
