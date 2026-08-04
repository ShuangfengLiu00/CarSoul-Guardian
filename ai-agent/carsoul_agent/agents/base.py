"""Base agent contract.

Every agent in CarSoul Guardian implements this interface so the system
can host multiple specialised agents behind one uniform API.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from carsoul_agent.config import settings
from carsoul_agent.memory import BaseMemory, ConversationMemory, Message, default_memory
from carsoul_agent.tools import ToolRegistry, default_registry


class BaseAgent(ABC):
    """Uniform agent interface."""

    name: str = "base_agent"
    description: str = ""

    def __init__(
        self,
        model_name: str | None = None,
        memory: BaseMemory | None = None,
        tools: ToolRegistry | None = None,
    ) -> None:
        self.model_name = model_name or settings.model_name
        self.memory = memory or default_memory
        self.tools = tools or default_registry
        self.settings = settings

    @abstractmethod
    def handle(self, message: str, user: str, session_id: str | None = None) -> dict[str, Any]:
        """Process a user message and return a result dict.

        Result must include at least `answer` and `agent_status`.
        """

    # ---- helpers shared by concrete agents ----
    def _ensure_session(self, session_id: str | None, user: str) -> str:
        return session_id or f"{user}:{hash(user) & 0xFFFFFFFF:x}"

    def _remember(self, session_id: str, role: str, content: str) -> None:
        self.memory.add(session_id, Message(role=role, content=content))
