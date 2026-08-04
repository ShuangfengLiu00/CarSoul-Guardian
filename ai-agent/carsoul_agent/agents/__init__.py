"""Agent layer: base contract, registry, concrete agents, and core workflow."""
from carsoul_agent.agents.base import BaseAgent
from carsoul_agent.agents.carsoul_agent import CarSoulGuardianAgent
from carsoul_agent.agents.core import (
    AgentState,
    CoreWorkflow,
    Trace,
    build_core_workflow,
    trace_entry,
)
from carsoul_agent.agents.registry import (
    AgentRegistry,
    get_agent_class,
    register_agent,
    registry,
)

__all__ = [
    "BaseAgent",
    "CarSoulGuardianAgent",
    "AgentRegistry",
    "registry",
    "register_agent",
    "get_agent_class",
    # Core workflow
    "AgentState",
    "CoreWorkflow",
    "Trace",
    "trace_entry",
    "build_core_workflow",
]
