"""Tool calling interface.

Tools are how agents reach into the real world (DB, APIs, sensors). Each
tool is self-describing so an LLM can select it. DB-backed tools are
implemented in ``vehicle_tools.py``; knowledge tools in ``knowledge_tool.py``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str = ""


class BaseTool(ABC):
    name: str = "base_tool"
    description: str = ""
    parameters: dict = {}  # JSON-schema-ish hint for the LLM

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with keyword arguments."""

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


class ToolRegistry:
    """Registry of tools available to agents."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def all(self) -> list[BaseTool]:
        return list(self._tools.values())


# Shared default registry.
default_registry = ToolRegistry()
