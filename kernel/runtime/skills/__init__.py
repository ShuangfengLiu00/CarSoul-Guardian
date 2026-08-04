"""Skill package for the CarSoul OS Runtime SDK.

This package contains:

- **Expert skill adapters** (:mod:`expert_skills`): 10 existing expert
  agents wrapped as :class:`~kernel.runtime.skill.Skill` implementations.
- **Agent presets** (:mod:`presets`): predefined skill compositions for
  common agent archetypes (guardian, battery_agent, safety_agent, etc.).

Quick start
-----------
::

    from kernel.runtime.skills import register_all_expert_skills
    from kernel.runtime.skills.presets import get_preset_skills

    # Register all 10 expert skills globally.
    register_all_expert_skills()

    # Or assemble an agent from a preset.
    guardian_skills = get_preset_skills("guardian")
"""
from kernel.runtime.skills.expert_skills import (
    ALL_EXPERT_SKILLS,
    ChassisSkill,
    ChargingIntelligenceSkill,
    DrivingBehaviorSkill,
    ElectricalSkill,
    EnergyOptimizationSkill,
    EnvironmentAdaptationSkill,
    ExpertSkillAdapter,
    MaintenanceSkill,
    PowertrainSkill,
    UserCompanionSkill,
    VehicleValueSkill,
    build_all_expert_skills,
    register_all_expert_skills,
)
from kernel.runtime.skills.presets import (
    AGENT_PRESETS,
    battery_agent_skills,
    energy_agent_skills,
    guardian_skills,
    get_preset_skills,
    list_presets,
    safety_agent_skills,
    value_agent_skills,
)

__all__ = [
    # Expert skill adapters
    "ExpertSkillAdapter",
    "PowertrainSkill",
    "ChassisSkill",
    "ElectricalSkill",
    "DrivingBehaviorSkill",
    "MaintenanceSkill",
    "VehicleValueSkill",
    "EnvironmentAdaptationSkill",
    "ChargingIntelligenceSkill",
    "EnergyOptimizationSkill",
    "UserCompanionSkill",
    "ALL_EXPERT_SKILLS",
    "build_all_expert_skills",
    "register_all_expert_skills",
    # Presets
    "guardian_skills",
    "battery_agent_skills",
    "safety_agent_skills",
    "value_agent_skills",
    "energy_agent_skills",
    "get_preset_skills",
    "list_presets",
    "AGENT_PRESETS",
]
