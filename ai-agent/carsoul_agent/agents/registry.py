"""Agent registry.

Central place to register and look up agents by name. The backend's
agent_service can use this to dispatch to different agents.
"""
from __future__ import annotations

from carsoul_agent.agents.base import BaseAgent


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, type[BaseAgent]] = {}

    def register(self, agent_cls: type[BaseAgent]) -> type[BaseAgent]:
        self._agents[agent_cls.name] = agent_cls
        return agent_cls

    def get(self, name: str) -> type[BaseAgent] | None:
        return self._agents.get(name)

    def names(self) -> list[str]:
        return list(self._agents.keys())


registry = AgentRegistry()


def register_agent(agent_cls: type[BaseAgent]) -> type[BaseAgent]:
    return registry.register(agent_cls)


def get_agent_class(name: str) -> type[BaseAgent] | None:
    return registry.get(name)
