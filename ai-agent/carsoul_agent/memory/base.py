"""Abstract memory interface.

Different backends (in-process dict, Redis, vector DB) implement this so
agents can swap memory strategies without changing their logic. Vector
long-term memory uses ChromaDB for vector recall.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)


class BaseMemory(ABC):
    """Memory contract every agent can rely on."""

    @abstractmethod
    def add(self, session_id: str, message: Message) -> None: ...

    @abstractmethod
    def history(self, session_id: str, limit: int = 20) -> list[Message]: ...

    @abstractmethod
    def clear(self, session_id: str) -> None: ...

    def as_chat_messages(self, session_id: str, limit: int = 20) -> list[dict]:
        """Return history in OpenAI chat format [{role, content}, ...]."""
        return [
            {"role": m.role, "content": m.content}
            for m in self.history(session_id, limit=limit)
            if m.role in {"user", "assistant", "system"}
        ]
