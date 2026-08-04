"""carsoul_os — top-level convenience import for the Runtime SDK.

This module re-exports the SDK's public API so external developers
can use the import style from the V1.0 development plan:

    from carsoul_os import create_agent, register_skill, execute_workflow

    agent = create_agent(name="my_guardian",
                         skills=[BatterySkill()],
                         memory="sqlite:///carsoul.db",
                         governance=GovernanceProfile(read_only=True))
    result = execute_workflow(agent, vehicle_frame, user_query="电池最近怎么样")
"""
from kernel.runtime import (
    AgentConfig,
    AgentWrapper,
    FORBIDDEN_TOOLS,
    GovernanceProfile,
    READ_TOOLS,
    Skill,
    SkillFinding,
    SkillRegistry,
    WorkflowResult,
    WRITE_TOOLS,
    create_agent,
    execute_workflow,
    get_preset_skills,
    get_skill_registry,
    list_presets,
    register_all_expert_skills,
    register_skill,
    reset_skill_registry,
)

__all__ = [
    "create_agent",
    "register_skill",
    "register_all_expert_skills",
    "execute_workflow",
    "get_preset_skills",
    "list_presets",
    "GovernanceProfile",
    "Skill",
    "SkillFinding",
    "WorkflowResult",
    "AgentWrapper",
    "AgentConfig",
    "SkillRegistry",
    "get_skill_registry",
    "reset_skill_registry",
    "READ_TOOLS",
    "WRITE_TOOLS",
    "FORBIDDEN_TOOLS",
]
