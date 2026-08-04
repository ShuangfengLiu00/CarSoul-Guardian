"""In-process conversation memory.

Good enough for single-instance dev / demo. Replace with Redis-backed
memory for multi-instance + long-term vector recall.
"""
from __future__ import annotations

from collections import defaultdict

from carsoul_agent.memory.base import BaseMemory, Message


class ConversationMemory(BaseMemory):
    def __init__(self) -> None:
        self._store: dict[str, list[Message]] = defaultdict(list)

    def add(self, session_id: str, message: Message) -> None:
        self._store[session_id].append(message)

    def history(self, session_id: str, limit: int = 20) -> list[Message]:
        return list(self._store.get(session_id, [])[-limit:])

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)
