"""Skill protocol and registry for the Runtime SDK.

A :class:`Skill` is a self-contained diagnostic capability that can be
registered and executed without modifying framework code.  This is the
foundation for Step 6 (专家 Skills 化), but the protocol is defined here
so the SDK natively supports custom skills.

Example
-------
::

    class MyBatterySkill:
        name = "my_battery_check"
        domain = "battery"

        def match(self, state):
            return "battery" in state.get("anomaly_topics", [])

        def run(self, state, tools, memory):
            return SkillFinding(
                specialty="battery",
                findings=[{"issue": "high temperature", "severity": "warning"}],
                severity="warning",
                recommendation="检查冷却系统",
                confidence=0.85,
            )

    register_skill(MyBatterySkill())
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from kernel.memory_engine import MemoryEngine
from kernel.runtime.governance import GovernanceProfile


# ------------------------------------------------------------------ #
#  SkillFinding — the output of a skill execution
# ------------------------------------------------------------------ #
@dataclass
class SkillFinding:
    """Structured output from a Skill execution.

    Attributes
    ----------
    specialty : str
        The domain this finding belongs to (e.g. "battery", "motor").
    findings : list[dict]
        Detailed findings, each a dict with at least "issue" and "severity".
    severity : str
        Overall severity: "normal", "warning", "critical".
    recommendation : str
        Natural-language recommendation for the user.
    confidence : float
        Confidence in the finding (0.0-1.0).
    """

    specialty: str
    findings: list[dict[str, Any]] = field(default_factory=list)
    severity: str = "normal"
    recommendation: str = ""
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "specialty": self.specialty,
            "findings": self.findings,
            "severity": self.severity,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
        }


# ------------------------------------------------------------------ #
#  Skill protocol
# ------------------------------------------------------------------ #
@runtime_checkable
class Skill(Protocol):
    """The skill protocol — implement this to create a custom skill.

    A skill is a self-contained diagnostic unit that:
    1. Decides whether it's relevant (``match``)
    2. Produces a structured finding (``run``)

    Skills are stateless: they receive the current state and produce
    findings without side effects (memory writes are handled by the
    workflow layer, not the skill itself).
    """

    name: str
    """Unique skill identifier."""

    domain: str
    """The vehicle domain this skill covers (battery/motor/chassis/etc)."""

    def match(self, state: dict[str, Any]) -> bool:
        """Return True if this skill is relevant to the current state.

        Args:
            state: The workflow state dict, containing at least:
                - ``anomaly_topics``: list[str] of active anomaly domains
                - ``anomalies``: list[dict] of detected anomalies
                - ``vehicle_frame``: the TelemetryFrame being analysed
        """
        ...

    def run(
        self,
        state: dict[str, Any],
        tools: Any,
        memory: MemoryEngine,
        knowledge: Any = None,
    ) -> SkillFinding:
        """Execute the skill and produce a finding.

        Args:
            state: The workflow state dict.
            tools: A governance-filtered tool registry (read-only by default).
            memory: The memory engine for recalling vehicle history.
            knowledge: Optional knowledge base / RAG context for grounding.

        Returns:
            A SkillFinding with the diagnostic result.
        """
        ...


# ------------------------------------------------------------------ #
#  SkillRegistry
# ------------------------------------------------------------------ #
class SkillRegistry:
    """Registry of custom skills available to SDK agents.

    Skills are registered globally via :func:`register_skill` and can
    be used by any agent created via :func:`create_agent`.
    """

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> Skill:
        """Register a skill. Returns the skill for chaining.

        Raises
        ------
        ValueError
            If a skill with the same name is already registered.
        """
        if not hasattr(skill, "name") or not skill.name:
            raise ValueError("技能必须有一个非空 name 属性")
        if not hasattr(skill, "domain"):
            raise ValueError("技能必须有 domain 属性")
        if skill.name in self._skills:
            raise ValueError(f"技能 '{skill.name}' 已注册")
        if not callable(getattr(skill, "match", None)):
            raise ValueError(f"技能 '{skill.name}' 必须实现 match 方法")
        if not callable(getattr(skill, "run", None)):
            raise ValueError(f"技能 '{skill.name}' 必须实现 run 方法")
        self._skills[skill.name] = skill
        return skill

    def unregister(self, name: str) -> bool:
        """Remove a skill by name. Returns True if it was found."""
        return self._skills.pop(name, None) is not None

    def get(self, name: str) -> Skill | None:
        """Fetch a skill by name."""
        return self._skills.get(name)

    def all(self) -> list[Skill]:
        """Return all registered skills."""
        return list(self._skills.values())

    def match_skills(self, state: dict[str, Any]) -> list[Skill]:
        """Return all skills whose ``match`` returns True for the state."""
        return [s for s in self._skills.values() if s.match(state)]

    def clear(self) -> None:
        """Remove all registered skills (mainly for tests)."""
        self._skills.clear()

    def count(self) -> int:
        """Number of registered skills."""
        return len(self._skills)


# Module-level singleton.
_default_registry = SkillRegistry()


def register_skill(skill: Skill) -> Skill:
    """Register a custom skill globally.

    This is the public API matching the dev plan:
    ``register_skill(MySkill())``

    Parameters
    ----------
    skill : Skill
        Any object implementing the Skill protocol (name, domain, match, run).

    Returns
    -------
    Skill
        The registered skill (for chaining).
    """
    return _default_registry.register(skill)


def get_skill_registry() -> SkillRegistry:
    """Return the global skill registry singleton."""
    return _default_registry


def reset_skill_registry() -> None:
    """Clear all registered skills (mainly for tests)."""
    _default_registry.clear()
