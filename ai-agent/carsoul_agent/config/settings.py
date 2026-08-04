"""Agent configuration (reads env shared with backend)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


@dataclass
class AgentSettings:
    model_name: str = field(default_factory=lambda: _env("MODEL_NAME", "gpt-4o-mini"))
    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY", ""))
    openai_api_base: str = field(default_factory=lambda: _env("OPENAI_API_BASE", ""))
    language: str = field(default_factory=lambda: _env("AGENT_LANGUAGE", "zh-CN"))
    proactive: bool = field(default_factory=lambda: _env("AGENT_PROACTIVE", "true").lower() == "true")
    vector_db_path: str = field(default_factory=lambda: _env("VECTOR_DB_PATH", "./ai-agent/memory/vector_store"))
    chroma_collection: str = field(default_factory=lambda: _env("CHROMA_COLLECTION", "carsoul_guardian"))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key)


settings = AgentSettings()
