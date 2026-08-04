"""Skill Registry — 技能注册中心 (§7 Skill Layer).

Implements the skill layer of the Governance Architecture: every discrete
capability an agent can perform is registered here as an independent
entity, decoupled from the agent itself.

A *skill* is a unit of expertise (e.g. ``battery_health_analysis``) that:

  - Belongs to exactly one agent (``agent_id``).
  - Declares an input/output schema so the orchestrator can validate
    calls before dispatch.
  - Carries runtime call statistics for observability.

This mirrors the pattern used by ``registry.py`` for ``AgentMetadata``:
a dataclass plus a central registry with lookup helpers and a singleton
instance seeded by ``register_governance_skills()``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """Rich metadata for a registered skill (§7 data structure).

    Mirrors the skill schema in the governance document:

        {
          "skill_id": "battery_health_analysis",
          "name": "Battery Health Analysis",
          "description": "电池健康度分析",
          "agent_id": "powertrain_expert",
          "version": "v1.0",
          "input_schema": {"soc": "float", "temperature": "float"},
          "output_schema": {"soh": "float", "degradation": "str"},
          "category": "analysis"
        }
    """

    skill_id: str
    name: str
    description: str
    agent_id: str  # Owning agent.
    version: str = "v1.0"
    input_schema: dict = field(default_factory=dict)  # Input parameter schema.
    output_schema: dict = field(default_factory=dict)  # Output parameter schema.
    call_conditions: str = ""  # Pre-conditions for invocation.
    category: str = "general"  # analysis / prediction / detection / diagnosis / recommendation.
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # Runtime stats (updated by record_call).
    total_calls: int = 0
    success_count: int = 0

    @property
    def success_rate(self) -> float:
        """Ratio of successful calls over total calls."""
        return self.success_count / self.total_calls if self.total_calls > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a dict suitable for API responses."""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "agent_id": self.agent_id,
            "version": self.version,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "call_conditions": self.call_conditions,
            "category": self.category,
            "registered_at": self.registered_at,
            "stats": {
                "total_calls": self.total_calls,
                "success_count": self.success_count,
                "success_rate": round(self.success_rate, 4),
            },
        }


class SkillRegistry:
    """Central registry for skills — discovery, lookup, and statistics.

    Extends the governance layer with:
      - Skill registration with rich schema metadata.
      - Discovery by agent, by category, or by id.
      - Runtime call statistics tracking (mirrors AgentMetadata stats).
    """

    def __init__(self) -> None:
        self._skills: dict[str, SkillMetadata] = {}

    # ---- Registration ------------------------------------------------
    def register(
        self,
        skill_id: str,
        name: str,
        description: str,
        agent_id: str,
        version: str = "v1.0",
        input_schema: dict | None = None,
        output_schema: dict | None = None,
        call_conditions: str = "",
        category: str = "general",
    ) -> SkillMetadata:
        """Register or update a skill's metadata."""
        meta = SkillMetadata(
            skill_id=skill_id,
            name=name,
            description=description,
            agent_id=agent_id,
            version=version,
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            call_conditions=call_conditions,
            category=category,
        )
        self._skills[skill_id] = meta
        logger.info("Skill registered: %s (%s) -> agent=%s", skill_id, name, agent_id)
        return meta

    # ---- Lookup ------------------------------------------------------
    def get(self, skill_id: str) -> SkillMetadata | None:
        """Return the skill metadata, or None if not found."""
        return self._skills.get(skill_id)

    def all_skills(self) -> list[SkillMetadata]:
        """Return all registered skills."""
        return list(self._skills.values())

    def names(self) -> list[str]:
        """Return all registered skill ids."""
        return list(self._skills.keys())

    def find_by_agent(self, agent_id: str) -> list[SkillMetadata]:
        """Find all skills owned by a given agent."""
        return [s for s in self._skills.values() if s.agent_id == agent_id]

    def find_by_category(self, category: str) -> list[SkillMetadata]:
        """Find all skills in a given category."""
        return [s for s in self._skills.values() if s.category == category]

    # ---- Stats (updated by the workflow engine) ---------------------
    def record_call(self, skill_id: str, success: bool) -> None:
        """Record a skill invocation result for statistics."""
        skill = self._skills.get(skill_id)
        if skill is None:
            logger.warning("record_call: unknown skill '%s'", skill_id)
            return
        skill.total_calls += 1
        if success:
            skill.success_count += 1

    # ---- Serialisation for API/frontend -----------------------------
    def to_dict(self) -> dict[str, Any]:
        """Serialise the entire registry for API/frontend."""
        return {
            "skill_count": len(self._skills),
            "categories": sorted({s.category for s in self._skills.values()}),
            "skills": [s.to_dict() for s in self._skills.values()],
        }


# ------------------------------------------------------------------ #
#  Singleton instance
# ------------------------------------------------------------------ #
skill_registry = SkillRegistry()


def register_governance_skills() -> None:
    """Pre-register all CarSoul skills into the skill registry.

    Called once at startup to populate the registry with ~30 skills
    covering every agent's capabilities — battery, driving, risk,
    diagnosis, maintenance, knowledge, and more.
    """
    # --- Orchestrator skills ---
    skill_registry.register(
        skill_id="intent_understanding",
        name="Intent Understanding",
        description="解析用户自然语言意图，识别车辆相关需求。",
        agent_id="carsoul_guardian",
        category="general",
        input_schema={"user_message": "str", "vehicle_state": "dict"},
        output_schema={"intent": "str", "confidence": "float", "slots": "dict"},
        call_conditions="用户发起对话时触发。",
    )
    skill_registry.register(
        skill_id="task_decomposition",
        name="Task Decomposition",
        description="将复杂任务拆解为子任务并分配给对应Agent。",
        agent_id="carsoul_guardian",
        category="general",
        input_schema={"intent": "str", "context": "dict"},
        output_schema={"subtasks": "list[dict]", "agent_assignments": "dict"},
        call_conditions="意图理解完成后触发。",
    )
    skill_registry.register(
        skill_id="result_fusion",
        name="Result Fusion",
        description="融合多Agent返回结果，生成统一输出。",
        agent_id="carsoul_guardian",
        category="general",
        input_schema={"agent_results": "list[dict]"},
        output_schema={"fused_result": "dict", "confidence": "float"},
        call_conditions="所有子Agent执行完毕后触发。",
    )

    # --- Perception skills ---
    skill_registry.register(
        skill_id="anomaly_detection",
        name="Anomaly Detection",
        description="基于阈值与语义模型检测车辆传感器异常。",
        agent_id="perception",
        category="detection",
        input_schema={"sensor_window": "list[dict]", "thresholds": "dict"},
        output_schema={"anomalies": "list[dict]", "severity": "str"},
        call_conditions="车辆状态数据可用时触发。",
    )
    skill_registry.register(
        skill_id="semantic_detection",
        name="Semantic Detection",
        description="语义级异常检测，识别复合型故障模式。",
        agent_id="perception",
        category="detection",
        input_schema={"sensor_window": "list[dict]", "vehicle_state": "dict"},
        output_schema={"semantic_anomalies": "list[dict]"},
        call_conditions="阈值检测完成后触发。",
    )

    # --- Diagnosis skills ---
    skill_registry.register(
        skill_id="fault_diagnosis",
        name="Fault Diagnosis",
        description="召集专科专家并行会诊，汇总统一故障诊断结论。",
        agent_id="diagnosis",
        category="diagnosis",
        input_schema={"anomalies": "list[dict]", "vehicle_state": "dict"},
        output_schema={"diagnosis": "dict", "root_cause": "str", "confidence": "float"},
        call_conditions="检测到异常后触发。",
    )
    skill_registry.register(
        skill_id="knowledge_qa",
        name="Knowledge QA",
        description="基于车辆知识库的问答检索能力。",
        agent_id="diagnosis",
        category="general",
        input_schema={"query": "str", "context": "dict"},
        output_schema={"answer": "str", "sources": "list[str]", "confidence": "float"},
        call_conditions="用户提出知识类问题时触发。",
    )

    # --- Risk skills ---
    skill_registry.register(
        skill_id="vehicle_risk_detection",
        name="Vehicle Risk Detection",
        description="检测车辆当前面临的各类风险。",
        agent_id="risk",
        category="detection",
        input_schema={"diagnosis": "dict", "trip_context": "dict"},
        output_schema={"risks": "list[dict]", "risk_level": "str"},
        call_conditions="诊断完成后触发。",
    )
    skill_registry.register(
        skill_id="risk_quantification",
        name="Risk Quantification",
        description="量化风险等级、发生概率与预计剩余可用时间。",
        agent_id="risk",
        category="analysis",
        input_schema={"diagnosis": "dict", "risk_history": "list[dict]"},
        output_schema={"risk_score": "float", "probability": "float", "eta_hours": "float"},
        call_conditions="风险检测完成后触发。",
    )

    # --- Explainer skills ---
    skill_registry.register(
        skill_id="technical_explanation",
        name="Technical Explanation",
        description="将技术诊断结果转化为用户可理解的自然语言解释。",
        agent_id="explainer",
        category="general",
        input_schema={"diagnosis": "dict", "risk_assessment": "dict"},
        output_schema={"explanation": "str", "language": "str"},
        call_conditions="诊断与风险评估完成后触发。",
    )
    skill_registry.register(
        skill_id="trip_report_generation",
        name="Trip Report Generation",
        description="生成结构化行程报告，包含健康度、风险、建议。",
        agent_id="explainer",
        category="general",
        input_schema={"trip_data": "dict", "diagnosis": "dict", "risk_assessment": "dict"},
        output_schema={"report": "dict", "format": "str"},
        call_conditions="行程结束后触发。",
    )
    skill_registry.register(
        skill_id="user_preference_analysis",
        name="User Preference Analysis",
        description="分析用户偏好以个性化解释内容与表达方式。",
        agent_id="explainer",
        category="analysis",
        input_schema={"driver_profile": "dict", "interaction_history": "list[dict]"},
        output_schema={"preferences": "dict", "communication_style": "str"},
        call_conditions="用户画像数据可用时触发。",
    )

    # --- Service skills ---
    skill_registry.register(
        skill_id="personalized_recommendation",
        name="Personalized Recommendation",
        description="基于诊断与用户偏好生成个性化行动建议。",
        agent_id="service",
        category="recommendation",
        input_schema={"diagnosis": "dict", "risk_assessment": "dict", "preferences": "dict"},
        output_schema={"recommendations": "list[dict]", "priority": "str"},
        call_conditions="诊断与偏好分析完成后触发。",
    )
    skill_registry.register(
        skill_id="reminder_generation",
        name="Reminder Generation",
        description="生成并推送保养、充电、检查等提醒。",
        agent_id="service",
        category="general",
        input_schema={"diagnosis": "dict", "maintenance_schedule": "dict"},
        output_schema={"reminders": "list[dict]", "channels": "list[str]"},
        call_conditions="诊断完成或定时触发。",
    )
    skill_registry.register(
        skill_id="charging_station_recommendation",
        name="Charging Station Recommendation",
        description="基于车辆位置与剩余电量推荐充电站。",
        agent_id="service",
        category="recommendation",
        input_schema={"location": "dict", "soc": "float", "range_km": "float"},
        output_schema={"stations": "list[dict]", "recommended": "str"},
        call_conditions="电量低于阈值或用户请求时触发。",
    )

    # --- Powertrain expert skills ---
    skill_registry.register(
        skill_id="battery_health_analysis",
        name="Battery Health Analysis",
        description="电池健康度(SOH)分析与退化趋势评估。",
        agent_id="powertrain_expert",
        category="analysis",
        input_schema={"soc": "float", "temperature": "float", "charging_history": "list[dict]"},
        output_schema={"soh": "float", "degradation": "str", "trend": "str"},
        call_conditions="电池数据可用时触发。",
    )
    skill_registry.register(
        skill_id="battery_failure_prediction",
        name="Battery Failure Prediction",
        description="预测电池潜在故障与剩余使用寿命。",
        agent_id="powertrain_expert",
        category="prediction",
        input_schema={"soh": "float", "cycle_count": "int", "temperature_history": "list[float]"},
        output_schema={"failure_probability": "float", "remaining_cycles": "int", "risk_level": "str"},
        call_conditions="健康度分析完成后触发。",
    )
    skill_registry.register(
        skill_id="thermal_risk_assessment",
        name="Thermal Risk Assessment",
        description="评估电池热失控风险等级与安全裕度。",
        agent_id="powertrain_expert",
        category="detection",
        input_schema={"temperature": "float", "temperature_gradient": "float", "soc": "float"},
        output_schema={"thermal_risk": "str", "safety_margin": "float", "advice": "str"},
        call_conditions="电池温度超过阈值时触发。",
    )
    skill_registry.register(
        skill_id="range_prediction",
        name="Range Prediction",
        description="基于电池状态与驾驶条件预测续航里程。",
        agent_id="powertrain_expert",
        category="prediction",
        input_schema={"soc": "float", "soh": "float", "driving_pattern": "dict", "environment": "dict"},
        output_schema={"range_km": "float", "confidence": "float", "factors": "list[str]"},
        call_conditions="电池与驾驶数据可用时触发。",
    )
    skill_registry.register(
        skill_id="charging_strategy_optimizer",
        name="Charging Strategy Optimizer",
        description="优化充电策略以延长电池寿命并满足出行需求。",
        agent_id="powertrain_expert",
        category="analysis",
        input_schema={"soc": "float", "soh": "float", "trip_plan": "dict", "electricity_price": "dict"},
        output_schema={"charging_plan": "dict", "estimated_cost": "float", "lifespan_impact": "str"},
        call_conditions="用户有出行计划或充电需求时触发。",
    )

    # --- Chassis expert skills ---
    skill_registry.register(
        skill_id="brake_analysis",
        name="Brake Analysis",
        description="刹车片磨损分析与制动性能评估。",
        agent_id="chassis_expert",
        category="analysis",
        input_schema={"brake_pad_remaining_km": "int", "brake_fluid_level": "float", "braking_history": "list[dict]"},
        output_schema={"brake_health": "str", "remaining_km": "int", "recommendation": "str"},
        call_conditions="制动系统数据可用时触发。",
    )
    skill_registry.register(
        skill_id="tire_analysis",
        name="Tire Analysis",
        description="轮胎胎纹深度与磨损模式分析。",
        agent_id="chassis_expert",
        category="analysis",
        input_schema={"tire_tread_mm": "float", "tire_pressure": "dict", "mileage": "int"},
        output_schema={"tire_health": "str", "wear_pattern": "str", "replacement_advice": "str"},
        call_conditions="轮胎数据可用时触发。",
    )

    # --- Electrical expert skills ---
    skill_registry.register(
        skill_id="sensor_diagnosis",
        name="Sensor Diagnosis",
        description="传感器读数诊断与异常定位。",
        agent_id="electrical_expert",
        category="diagnosis",
        input_schema={"sensor_readings": "dict", "expected_ranges": "dict"},
        output_schema={"faulty_sensors": "list[str]", "diagnosis": "dict", "confidence": "float"},
        call_conditions="传感器数据异常时触发。",
    )
    skill_registry.register(
        skill_id="fault_code_analysis",
        name="Fault Code Analysis",
        description="解析车辆故障码并匹配根因知识。",
        agent_id="electrical_expert",
        category="diagnosis",
        input_schema={"fault_codes": "list[str]", "vehicle_state": "dict"},
        output_schema={"interpreted_codes": "list[dict]", "root_causes": "list[str]"},
        call_conditions="存在故障码时触发。",
    )

    # --- Driving expert skills ---
    skill_registry.register(
        skill_id="driving_pattern_analysis",
        name="Driving Pattern Analysis",
        description="分析驾驶行为模式（急加速、急刹车等）。",
        agent_id="driving_expert",
        category="analysis",
        input_schema={"driving_behavior": "dict", "trip_history": "list[dict]"},
        output_schema={"patterns": "dict", "risk_factors": "list[str]", "score": "float"},
        call_conditions="驾驶行为数据可用时触发。",
    )
    skill_registry.register(
        skill_id="safety_assessment",
        name="Safety Assessment",
        description="综合评估驾驶安全等级与风险点。",
        agent_id="driving_expert",
        category="analysis",
        input_schema={"driving_behavior": "dict", "safety_score": "float", "vehicle_state": "dict"},
        output_schema={"safety_level": "str", "risk_points": "list[dict]", "advice": "str"},
        call_conditions="驾驶模式分析完成后触发。",
    )
    skill_registry.register(
        skill_id="energy_consumption_analysis",
        name="Energy Consumption Analysis",
        description="分析能耗水平与节能优化空间。",
        agent_id="driving_expert",
        category="analysis",
        input_schema={"driving_behavior": "dict", "energy_data": "dict", "environment": "dict"},
        output_schema={"consumption_kwh_per_100km": "float", "efficiency": "str", "suggestions": "list[str]"},
        call_conditions="能耗数据可用时触发。",
    )
    skill_registry.register(
        skill_id="environment_impact_analysis",
        name="Environment Impact Analysis",
        description="评估驾驶行为对环境的影响（碳排放等）。",
        agent_id="driving_expert",
        category="analysis",
        input_schema={"driving_behavior": "dict", "energy_data": "dict"},
        output_schema={"carbon_footprint": "float", "eco_score": "float", "comparison": "dict"},
        call_conditions="能耗分析完成后触发。",
    )

    # --- Maintenance expert skills ---
    skill_registry.register(
        skill_id="maintenance_prediction",
        name="Maintenance Prediction",
        description="预测下次保养时间与保养项目。",
        agent_id="maintenance_expert",
        category="prediction",
        input_schema={"mileage": "int", "health_score": "float", "maintenance_history": "list[dict]"},
        output_schema={"next_service_km": "int", "items": "list[str]", "urgency": "str"},
        call_conditions="保养历史与里程数据可用时触发。",
    )
    skill_registry.register(
        skill_id="cost_estimation",
        name="Cost Estimation",
        description="估算维修保养费用。",
        agent_id="maintenance_expert",
        category="analysis",
        input_schema={"diagnosis": "dict", "maintenance_items": "list[str]", "region": "str"},
        output_schema={"estimated_cost": "float", "breakdown": "dict", "currency": "str"},
        call_conditions="诊断或保养项目确定后触发。",
    )
    skill_registry.register(
        skill_id="vehicle_valuation",
        name="Vehicle Valuation",
        description="评估车辆当前市场价值。",
        agent_id="maintenance_expert",
        category="analysis",
        input_schema={"health_score": "float", "mileage": "int", "age_years": "int", "model": "str"},
        output_schema={"market_value": "float", "valuation_range": "dict", "factors": "dict"},
        call_conditions="健康度与车辆信息可用时触发。",
    )
    skill_registry.register(
        skill_id="depreciation_forecast",
        name="Depreciation Forecast",
        description="预测车辆未来贬值趋势。",
        agent_id="maintenance_expert",
        category="prediction",
        input_schema={"current_value": "float", "age_years": "int", "mileage": "int", "market_trend": "dict"},
        output_schema={"forecast": "list[dict]", "annual_depreciation": "float"},
        call_conditions="估值完成后触发。",
    )
    skill_registry.register(
        skill_id="health_score_computation",
        name="Health Score Computation",
        description="综合计算车辆整体健康评分。",
        agent_id="maintenance_expert",
        category="analysis",
        input_schema={"battery_health": "float", "brake_health": "str", "tire_health": "str", "engine_health": "float"},
        output_schema={"health_score": "float", "grade": "str", "breakdown": "dict"},
        call_conditions="各子系统健康数据可用时触发。",
    )
    skill_registry.register(
        skill_id="lifecycle_prediction",
        name="Lifecycle Prediction",
        description="预测车辆关键部件生命周期节点。",
        agent_id="maintenance_expert",
        category="prediction",
        input_schema={"health_score": "float", "mileage": "int", "component_states": "dict"},
        output_schema={"lifecycle_events": "list[dict]", "estimated_lifespan_km": "int"},
        call_conditions="健康评分计算完成后触发。",
    )

    # --- Judge skills ---
    skill_registry.register(
        skill_id="conflict_resolution",
        name="Conflict Resolution",
        description="多专家意见冲突时的加权仲裁与决策融合。",
        agent_id="judge",
        category="general",
        input_schema={"expert_opinions": "list[dict]", "diagnosis": "dict"},
        output_schema={"verdict": "str", "primary_cause": "str", "confidence": "float", "weights": "dict"},
        call_conditions="专家意见不一致时触发。",
    )

    logger.info("Skill registry initialised with %d skills", len(skill_registry.names()))
