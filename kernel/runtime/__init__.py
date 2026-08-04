"""CarSoul OS Runtime SDK — the developer-facing "facade".

This package wraps the existing infrastructure (memory engine, digital
twin, governance, skills) into a clean public API that external
developers can use to create and run custom car agents.

Public API
----------
- :func:`create_agent` — create a custom agent with memory + governance
- :func:`register_skill` — register a custom diagnostic skill
- :func:`execute_workflow` — run a diagnostic workflow
- :class:`GovernanceProfile` — configure what an agent may do
- :class:`Skill` — the skill protocol
- :class:`SkillFinding` — structured skill output
- :class:`WorkflowResult` — structured workflow output
- :class:`AgentWrapper` — the agent object returned by create_agent

Quick start (≤20 lines)
-----------------------
::

    from kernel.runtime import (
        create_agent, register_skill, execute_workflow,
        GovernanceProfile, Skill, SkillFinding,
    )

    class BatterySkill:
        name = "battery_check"
        domain = "battery"
        def match(self, state):
            return "battery" in state.get("anomaly_topics", [])
        def run(self, state, tools, memory):
            return SkillFinding("battery", recommendation="检查电池冷却")

    agent = create_agent("my_guardian", skills=[BatterySkill()],
                         memory="sqlite:///carsoul.db")
    result = execute_workflow(agent, frames, "电池最近怎么样")
    print(result.answer)
"""
from kernel.runtime.agent import AgentConfig, AgentWrapper, create_agent
from kernel.runtime.governance import (
    FORBIDDEN_TOOLS,
    GovernanceProfile,
    READ_TOOLS,
    WRITE_TOOLS,
)
from kernel.runtime.skill import (
    Skill,
    SkillFinding,
    SkillRegistry,
    get_skill_registry,
    register_skill,
    reset_skill_registry,
)
from kernel.runtime.skills import (
    register_all_expert_skills,
    build_all_expert_skills,
    get_preset_skills,
    list_presets,
)
from kernel.runtime.workflow import WorkflowResult, execute_workflow

__all__ = [
    # Agent API
    "create_agent",
    "AgentWrapper",
    "AgentConfig",
    # Skill API
    "register_skill",
    "register_all_expert_skills",
    "build_all_expert_skills",
    "get_preset_skills",
    "list_presets",
    "Skill",
    "SkillFinding",
    "SkillRegistry",
    "get_skill_registry",
    "reset_skill_registry",
    # Workflow API
    "execute_workflow",
    "WorkflowResult",
    # Governance
    "GovernanceProfile",
    "READ_TOOLS",
    "WRITE_TOOLS",
    "FORBIDDEN_TOOLS",
]
