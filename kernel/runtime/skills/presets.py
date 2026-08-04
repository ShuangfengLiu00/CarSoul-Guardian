"""Agent skill presets — predefined skill compositions for common agents.

The dev plan specifies:
    agents/ 下的 Agent = 技能的编排组合
    (guardian = 全量技能 + 汇总；battery_agent = battery + safety 子集)

This module provides factory functions that return skill lists for
common agent archetypes, making it easy to create specialised agents
without manually assembling skill lists.
"""
from __future__ import annotations

from typing import Any

from kernel.runtime.skill import Skill


# ------------------------------------------------------------------ #
#  Preset factories
# ------------------------------------------------------------------ #
def guardian_skills() -> list[Any]:
    """All 10 expert skills — the full guardian agent.

    The guardian is the comprehensive agent that convenes all
    specialists for a complete consultation.

    Returns
    -------
    list[ExpertSkillAdapter]
        All 10 expert skill instances.
    """
    from kernel.runtime.skills.expert_skills import build_all_expert_skills
    return build_all_expert_skills()


def battery_agent_skills() -> list[Any]:
    """Battery + safety subset — the battery-focused agent.

    A lightweight agent focused on battery health and safety,
    suitable for scenarios where only battery-related diagnosis
    is needed.

    Returns
    -------
    list[ExpertSkillAdapter]
        PowertrainSkill + ChassisSkill + ChargingIntelligenceSkill.
    """
    from kernel.runtime.skills.expert_skills import (
        ChassisSkill,
        ChargingIntelligenceSkill,
        PowertrainSkill,
    )
    return [PowertrainSkill(), ChassisSkill(), ChargingIntelligenceSkill()]


def safety_agent_skills() -> list[Any]:
    """Safety-focused subset — brake / tire / driving behavior.

    Returns
    -------
    list[ExpertSkillAdapter]
        ChassisSkill + DrivingBehaviorSkill + EnvironmentAdaptationSkill.
    """
    from kernel.runtime.skills.expert_skills import (
        ChassisSkill,
        DrivingBehaviorSkill,
        EnvironmentAdaptationSkill,
    )
    return [ChassisSkill(), DrivingBehaviorSkill(), EnvironmentAdaptationSkill()]


def value_agent_skills() -> list[Any]:
    """Value-focused subset — valuation + maintenance + companion.

    Returns
    -------
    list[ExpertSkillAdapter]
        VehicleValueSkill + MaintenanceSkill + UserCompanionSkill.
    """
    from kernel.runtime.skills.expert_skills import (
        MaintenanceSkill,
        UserCompanionSkill,
        VehicleValueSkill,
    )
    return [VehicleValueSkill(), MaintenanceSkill(), UserCompanionSkill()]


def energy_agent_skills() -> list[Any]:
    """Energy-focused subset — charging + energy optimization.

    Returns
    -------
    list[ExpertSkillAdapter]
        ChargingIntelligenceSkill + EnergyOptimizationSkill.
    """
    from kernel.runtime.skills.expert_skills import (
        ChargingIntelligenceSkill,
        EnergyOptimizationSkill,
    )
    return [ChargingIntelligenceSkill(), EnergyOptimizationSkill()]


# ------------------------------------------------------------------ #
#  Preset registry
# ------------------------------------------------------------------ #
AGENT_PRESETS: dict[str, str] = {
    "guardian": "全量技能 + 汇总（10 个专家）",
    "battery_agent": "battery + safety 子集（动力系统 + 底盘 + 充电智能）",
    "safety_agent": "安全子集（底盘 + 驾驶行为 + 环境适应）",
    "value_agent": "价值子集（车辆价值 + 保养 + 用户陪伴）",
    "energy_agent": "能耗子集（充电智能 + 能耗优化）",
}

_PRESET_FACTORIES = {
    "guardian": guardian_skills,
    "battery_agent": battery_agent_skills,
    "safety_agent": safety_agent_skills,
    "value_agent": value_agent_skills,
    "energy_agent": energy_agent_skills,
}


def get_preset_skills(preset_name: str) -> list[Any]:
    """Get the skill list for a named agent preset.

    Parameters
    ----------
    preset_name : str
        One of: "guardian", "battery_agent", "safety_agent",
        "value_agent", "energy_agent".

    Returns
    -------
    list[Skill]
        The skill instances for the preset.

    Raises
    ------
    ValueError
        If the preset name is not recognised.
    """
    factory = _PRESET_FACTORIES.get(preset_name)
    if factory is None:
        raise ValueError(
            f"未知预设 '{preset_name}'，可选：{', '.join(_PRESET_FACTORIES.keys())}"
        )
    return factory()


def list_presets() -> dict[str, str]:
    """Return all available presets with descriptions."""
    return dict(AGENT_PRESETS)
