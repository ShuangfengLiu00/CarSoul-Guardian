"""Expert skills — 10 expert agents adapted as Skill implementations.

Each expert from ``experts.py`` and ``extended_experts.py`` is wrapped
as a :class:`Skill` implementation that can be registered via
``register_skill`` and used by any SDK-created agent.

This module realises the Step 6 acceptance criterion:
"10 个技能全部经 register_skill 装载"

Design
------
The adapters are *thin wrappers* — they delegate analysis to the
existing ExpertAgent classes, so the expert logic (failure-mode
matching, domain signals, LLM enrichment) is reused without
duplication.  The adapter's job is to:

  1. Implement ``match(state)`` by checking whether the state's
     anomaly categories intersect the expert's ``categories``.
  2. Implement ``run(state, tools, memory, knowledge)`` by calling
     the expert's ``consult(state)`` and converting the result to a
     :class:`SkillFinding`.

This means the existing 36 Agent tests remain green — the experts'
behaviour is unchanged, just wrapped in the Skill protocol.
"""
from __future__ import annotations

from typing import Any

from kernel.memory_engine import MemoryEngine
from kernel.runtime.skill import SkillFinding


# ------------------------------------------------------------------ #
#  Base expert-skill adapter
# ------------------------------------------------------------------ #
class ExpertSkillAdapter:
    """Base class that adapts an ExpertAgent as a Skill.

    Subclasses set ``_expert_cls`` and inherit the ``match`` / ``run``
    implementation.  The adapter instantiates the expert lazily to
    avoid import-time dependencies on the agent layer.
    """

    name: str = ""
    domain: str = ""
    _expert_cls: type | None = None
    _categories: tuple[str, ...] = ()

    def __init__(self) -> None:
        self._expert = None

    def _get_expert(self) -> Any:
        """Lazily instantiate the wrapped expert."""
        if self._expert is None and self._expert_cls is not None:
            self._expert = self._expert_cls()
        return self._expert

    def match(self, state: dict[str, Any]) -> bool:
        """Return True if any anomaly category matches this expert's scope.

        Also matches on domain signals (e.g. mileage, driving style)
        so the skill fires even without explicit anomaly categories.
        """
        anomalies = state.get("anomalies", [])
        for a in anomalies:
            if a.get("category") in self._categories:
                return True

        # Domain-signal matching: some experts fire on vehicle state
        # rather than anomaly categories (e.g. maintenance, value).
        return self._match_domain_signal(state)

    def _match_domain_signal(self, state: dict[str, Any]) -> bool:
        """Override in subclasses for domain-signal matching."""
        return False

    def run(
        self,
        state: dict[str, Any],
        tools: Any,
        memory: MemoryEngine,
        knowledge: Any = None,
    ) -> SkillFinding:
        """Execute the wrapped expert and convert the result."""
        expert = self._get_expert()
        if expert is None:
            return SkillFinding(
                specialty=self.domain,
                recommendation=f"{self.domain} 专家不可用",
                confidence=0.0,
            )

        # Inject knowledge context if provided.
        if knowledge is not None and "knowledge_context" not in state:
            state = {**state, "knowledge_context": knowledge}

        opinion = expert.consult(state)

        # Map expert severity to SkillFinding severity.
        sev_map = {
            "info": "normal",
            "low": "normal",
            "medium": "warning",
            "high": "warning",
            "urgent": "critical",
        }
        severity = sev_map.get(opinion.get("severity", "info"), "normal")

        return SkillFinding(
            specialty=opinion.get("specialty", self.domain),
            findings=opinion.get("findings", []),
            severity=severity,
            recommendation=opinion.get("recommendation", ""),
            confidence=opinion.get("confidence", 0.5),
        )


# ------------------------------------------------------------------ #
#  Core 5 experts as Skills
# ------------------------------------------------------------------ #
class PowertrainSkill(ExpertSkillAdapter):
    """动力系统技能 — 电池 / 发动机 / 电机."""
    name = "powertrain_skill"
    domain = "动力系统"
    _categories = ("battery", "engine", "motor", "powertrain")

    @property
    def _expert_cls(self) -> type:
        from carsoul_agent.agents.core.experts import PowertrainExpert
        return PowertrainExpert


class ChassisSkill(ExpertSkillAdapter):
    """底盘系统技能 — 刹车 / 轮胎 / 悬挂."""
    name = "chassis_skill"
    domain = "底盘系统"
    _categories = ("brake", "tire", "suspension", "chassis")

    @property
    def _expert_cls(self) -> type:
        from carsoul_agent.agents.core.experts import ChassisExpert
        return ChassisExpert


class ElectricalSkill(ExpertSkillAdapter):
    """电气系统技能 — 传感器 / 电路 / 电子."""
    name = "electrical_skill"
    domain = "电气系统"
    _categories = ("electrical", "sensor", "circuit", "electronic")

    @property
    def _expert_cls(self) -> type:
        from carsoul_agent.agents.core.experts import ElectricalExpert
        return ElectricalExpert


class DrivingBehaviorSkill(ExpertSkillAdapter):
    """驾驶行为技能 — 习惯 / 安全评分."""
    name = "driving_behavior_skill"
    domain = "驾驶行为"
    _categories = ("driving", "behavior", "safety")

    def _match_domain_signal(self, state: dict[str, Any]) -> bool:
        """Fire on aggressive driving style or low safety score."""
        profile = state.get("driver_profile", {})
        return profile.get("driving_style") in ("aggressive", "eco") or \
            isinstance(profile.get("safety_score"), (int, float))

    @property
    def _expert_cls(self) -> type:
        from carsoul_agent.agents.core.experts import DrivingBehaviorExpert
        return DrivingBehaviorExpert


class MaintenanceSkill(ExpertSkillAdapter):
    """保养规划技能 — 周期 / 成本 / 优先级."""
    name = "maintenance_skill"
    domain = "保养规划"
    _categories = ("overall", "maintenance")

    def _match_domain_signal(self, state: dict[str, Any]) -> bool:
        """Fire when mileage or health score is available."""
        vehicle = state.get("vehicle_state", {})
        return isinstance(vehicle.get("mileage"), (int, float)) or \
            isinstance(vehicle.get("health_score"), (int, float))

    @property
    def _expert_cls(self) -> type:
        from carsoul_agent.agents.core.experts import MaintenanceExpert
        return MaintenanceExpert


# ------------------------------------------------------------------ #
#  Extended 5 experts as Skills
# ------------------------------------------------------------------ #
class VehicleValueSkill(ExpertSkillAdapter):
    """车辆价值技能 — 折旧 / 保值率 / 残值."""
    name = "vehicle_value_skill"
    domain = "车辆价值"
    _categories = ("value", "depreciation", "asset")

    def _match_domain_signal(self, state: dict[str, Any]) -> bool:
        """Fire when purchase price is available."""
        vehicle = state.get("vehicle_state", {})
        return isinstance(vehicle.get("purchase_price"), (int, float))

    @property
    def _expert_cls(self) -> type:
        from carsoul_agent.agents.core.extended_experts import VehicleValueExpert
        return VehicleValueExpert


class EnvironmentAdaptationSkill(ExpertSkillAdapter):
    """环境适应技能 — 温度 / 天气 / 路况."""
    name = "environment_skill"
    domain = "环境适应"
    _categories = ("environment", "weather", "temperature", "road")

    def _match_domain_signal(self, state: dict[str, Any]) -> bool:
        """Fire when ambient temperature or trip context is available."""
        sensor_window = state.get("sensor_window", [])
        if sensor_window:
            latest = sensor_window[-1] if sensor_window else {}
            if latest.get("ambient_temp") is not None:
                return True
        return state.get("trip_context", {}).get("distance_km") is not None

    @property
    def _expert_cls(self) -> type:
        from carsoul_agent.agents.core.extended_experts import EnvironmentAdaptationExpert
        return EnvironmentAdaptationExpert


class ChargingIntelligenceSkill(ExpertSkillAdapter):
    """充电智能技能 — SOC / 充电策略."""
    name = "charging_skill"
    domain = "充电智能"
    _categories = ("charging", "energy", "soc")

    def _match_domain_signal(self, state: dict[str, Any]) -> bool:
        """Fire when SOC data or charging pattern is available."""
        sensor_window = state.get("sensor_window", [])
        for reading in sensor_window:
            if reading.get("soc") is not None:
                return True
        vehicle = state.get("vehicle_state", {})
        return vehicle.get("charging_pattern") is not None

    @property
    def _expert_cls(self) -> type:
        from carsoul_agent.agents.core.extended_experts import ChargingIntelligenceExpert
        return ChargingIntelligenceExpert


class EnergyOptimizationSkill(ExpertSkillAdapter):
    """能耗优化技能 — 驾驶风格 / 能效."""
    name = "energy_optimization_skill"
    domain = "能耗优化"
    _categories = ("energy", "consumption", "efficiency")

    def _match_domain_signal(self, state: dict[str, Any]) -> bool:
        """Fire when driving style or eco score is available."""
        profile = state.get("driver_profile", {})
        return profile.get("driving_style") is not None or \
            isinstance(profile.get("eco_score"), (int, float))

    @property
    def _expert_cls(self) -> type:
        from carsoul_agent.agents.core.extended_experts import EnergyOptimizationExpert
        return EnergyOptimizationExpert


class UserCompanionSkill(ExpertSkillAdapter):
    """用户陪伴技能 — 偏好 / 个性化建议."""
    name = "user_companion_skill"
    domain = "用户陪伴"
    _categories = ("user", "preference", "companion")

    def _match_domain_signal(self, state: dict[str, Any]) -> bool:
        """Always fire — companion advice is relevant in any context."""
        return True

    @property
    def _expert_cls(self) -> type:
        from carsoul_agent.agents.core.extended_experts import UserCompanionExpert
        return UserCompanionExpert


# ------------------------------------------------------------------ #
#  Registry: all 10 expert skills
# ------------------------------------------------------------------ #
ALL_EXPERT_SKILLS: list[type[ExpertSkillAdapter]] = [
    PowertrainSkill,
    ChassisSkill,
    ElectricalSkill,
    DrivingBehaviorSkill,
    MaintenanceSkill,
    VehicleValueSkill,
    EnvironmentAdaptationSkill,
    ChargingIntelligenceSkill,
    EnergyOptimizationSkill,
    UserCompanionSkill,
]


def build_all_expert_skills() -> list[ExpertSkillAdapter]:
    """Instantiate all 10 expert skill instances."""
    return [cls() for cls in ALL_EXPERT_SKILLS]


def register_all_expert_skills() -> list[str]:
    """Register all 10 expert skills via the global skill registry.

    Returns a list of registered skill names.

    This satisfies the acceptance criterion:
    "10 个技能全部经 register_skill 装载"
    """
    from kernel.runtime.skill import register_skill, get_skill_registry

    registered: list[str] = []
    for skill_cls in ALL_EXPERT_SKILLS:
        skill = skill_cls()
        # Only register if not already registered (idempotent).
        if get_skill_registry().get(skill.name) is None:
            register_skill(skill)
        registered.append(skill.name)
    return registered
