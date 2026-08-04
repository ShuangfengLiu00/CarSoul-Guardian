"""Agent creation for the Runtime SDK.

The :func:`create_agent` function is the primary entry point for
external developers.  It wraps the existing infrastructure (memory
engine, tool registry, governance, skills) into a single
:class:`AgentWrapper` that can be passed to :func:`execute_workflow`.

Design
------
The agent wrapper is deliberately lightweight — it holds configuration
and references to engine instances, not business logic.  The actual
workflow execution lives in :mod:`kernel.runtime.workflow`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kernel.memory_engine import MemoryEngine, Source
from kernel.runtime.governance import GovernanceProfile, READ_TOOLS
from kernel.runtime.skill import Skill, SkillRegistry, get_skill_registry


@dataclass
class AgentConfig:
    """Configuration for an SDK-created agent.

    Attributes
    ----------
    name : str
        Agent name (used in trace, memory source, etc.).
    skills : list[Skill]
        Skills this agent can use.  These are registered both locally
        (on the agent) and globally (in the skill registry).
    memory : str
        SQLite connection string for the memory engine.
        ``"sqlite:///:memory:"`` for testing, ``"sqlite:///carsoul.db"``
        for persistence.
    governance : GovernanceProfile
        What the agent is allowed to do.  Defaults to read-only.
    """

    name: str
    skills: list[Skill] = field(default_factory=list)
    memory: str = "sqlite:///:memory:"
    governance: GovernanceProfile = field(default_factory=GovernanceProfile)


class AgentWrapper:
    """A configured agent, ready for workflow execution.

    Created by :func:`create_agent`.  Holds references to:
    - The memory engine (persistent vehicle memory)
    - The governance profile (tool whitelist enforcement)
    - The agent's skills (local + global registry)
    - A governance-filtered view of available tools

    Attributes
    ----------
    config : AgentConfig
        The agent's configuration.
    memory_engine : MemoryEngine
        The persistent memory engine instance.
    """

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self._memory_engine = MemoryEngine(config.memory)

        # Register the agent's skills both locally and globally.
        self._local_skills: dict[str, Skill] = {}
        global_registry = get_skill_registry()
        for skill in config.skills:
            self._local_skills[skill.name] = skill
            # Register globally only if not already there.
            if global_registry.get(skill.name) is None:
                global_registry.register(skill)

    # ------------------------------------------------------------------ #
    #  Properties
    # ------------------------------------------------------------------ #
    @property
    def name(self) -> str:
        return self.config.name

    @property
    def governance(self) -> GovernanceProfile:
        return self.config.governance

    @property
    def memory_engine(self) -> MemoryEngine:
        return self._memory_engine

    @property
    def skills(self) -> list[Skill]:
        return list(self._local_skills.values())

    @property
    def allowed_tools(self) -> frozenset[str]:
        """The effective tool whitelist under this agent's governance."""
        return self.config.governance.effective_allowed()

    # ------------------------------------------------------------------ #
    #  Memory convenience methods
    # ------------------------------------------------------------------ #
    def remember(
        self,
        vehicle_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        impact_target: str | None = None,
        impact_delta: float = 0.0,
        confidence: float = 1.0,
        source: str | Source = Source.AGENT,
    ):
        """Record a vehicle memory via this agent.

        This is the SDK's native memory hook — any code that creates
        an agent via ``create_agent`` automatically gets persistent
        memory without importing the memory engine directly.
        """
        return self._memory_engine.remember(
            vehicle_id=vehicle_id,
            event_type=event_type,
            payload=payload,
            impact_target=impact_target,
            impact_delta=impact_delta,
            confidence=confidence,
            source=source,
        )

    def recall(self, vehicle_id: str, **kwargs):
        """Recall memories for a vehicle."""
        return self._memory_engine.recall(vehicle_id, **kwargs)

    def memory_summary(self, vehicle_id: str):
        """Get a token-budgeted memory summary for agent injection."""
        return self._memory_engine.summarize_for_agent(vehicle_id)

    # ------------------------------------------------------------------ #
    #  Governance
    # ------------------------------------------------------------------ #
    def validate_tool(self, tool_name: str) -> tuple[bool, str]:
        """Check if a tool call is allowed under governance."""
        return self.config.governance.validate_tool(tool_name)

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed (convenience wrapper)."""
        return self.config.governance.is_tool_allowed(tool_name)

    def call_tool(self, tool_name: str, **kwargs: Any) -> dict[str, Any]:
        """Call a tool with governance enforcement.

        Returns a dict with:
        - ``ok``: whether the call succeeded
        - ``data``: the tool result (if ok)
        - ``error``: error message (if not ok)
        - ``governance_blocked``: True if blocked by governance
        """
        allowed, reason = self.validate_tool(tool_name)
        if not allowed:
            return {
                "ok": False,
                "data": None,
                "error": reason,
                "governance_blocked": True,
            }

        # In the SDK's standalone mode, we don't have the full tool
        # registry from the agent layer.  The tools are available when
        # the agent layer is importable; otherwise we return a
        # "not available" result.
        try:
            from carsoul_agent.tools import default_registry
            tool = default_registry.get(tool_name)
            if tool is None:
                return {
                    "ok": False,
                    "data": None,
                    "error": f"工具 '{tool_name}' 不存在",
                    "governance_blocked": False,
                }
            result = tool.run(**kwargs)
            return {
                "ok": result.ok,
                "data": result.data,
                "error": result.error,
                "governance_blocked": False,
            }
        except ImportError:
            return {
                "ok": False,
                "data": None,
                "error": "工具层不可用（SDK 独立模式）",
                "governance_blocked": False,
            }

    # ------------------------------------------------------------------ #
    #  Skill matching
    # ------------------------------------------------------------------ #
    def match_skills(self, state: dict[str, Any]) -> list[Skill]:
        """Return skills (local + global) that match the current state."""
        matched: list[Skill] = []
        seen: set[str] = set()

        # Local skills first (agent-specific).
        for skill in self._local_skills.values():
            if skill.name not in seen and skill.match(state):
                matched.append(skill)
                seen.add(skill.name)

        # Global skills (registered via register_skill).
        for skill in get_skill_registry().all():
            if skill.name not in seen and skill.match(state):
                matched.append(skill)
                seen.add(skill.name)

        return matched

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #
    def close(self) -> None:
        """Release resources (close the memory engine)."""
        self._memory_engine.close()

    def to_dict(self) -> dict[str, Any]:
        """Serialise agent info for debugging."""
        return {
            "name": self.config.name,
            "skill_count": len(self._local_skills),
            "skill_names": [s.name for s in self._local_skills.values()],
            "governance": self.config.governance.to_dict(),
            "memory": self._memory_engine.count(),
        }


# ------------------------------------------------------------------ #
#  Public API: create_agent
# ------------------------------------------------------------------ #
def create_agent(
    name: str,
    skills: list[Skill] | None = None,
    memory: str = "sqlite:///:memory:",
    governance: GovernanceProfile | None = None,
) -> AgentWrapper:
    """Create a custom car agent with memory and governance.

    This is the primary SDK entry point.  It wraps the existing
    memory engine, tool registry, and governance system into a single
    agent that can execute workflows.

    Parameters
    ----------
    name : str
        Agent name (e.g. "my_guardian").
    skills : list[Skill], optional
        Custom skills for this agent.  Each skill must implement the
        Skill protocol (name, domain, match, run).
    memory : str
        SQLite connection string.  Use ``"sqlite:///carsoul.db"`` for
        persistence across restarts.
    governance : GovernanceProfile, optional
        What the agent is allowed to do.  Defaults to read-only.

    Returns
    -------
    AgentWrapper
        A configured agent, ready for :func:`execute_workflow`.

    Example
    -------
    ::

        from kernel.runtime import create_agent, GovernanceProfile

        agent = create_agent(
            name="my_guardian",
            skills=[MyBatterySkill()],
            memory="sqlite:///carsoul.db",
            governance=GovernanceProfile(read_only=True),
        )
    """
    config = AgentConfig(
        name=name,
        skills=skills or [],
        memory=memory,
        governance=governance or GovernanceProfile(),
    )
    return AgentWrapper(config)
