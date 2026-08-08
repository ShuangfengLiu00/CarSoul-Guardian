"""Application configuration.

Reads from environment / `.env`. Designed so the backend can boot in
development even without a running PostgreSQL (falls back to SQLite),
while production uses the real DATABASE_URL.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_env() -> Path:
    """Locate the nearest .env file (project root, then backend/)."""
    here = Path(__file__).resolve()
    candidates = [
        here.parent.parent.parent / ".env",   # project root
        here.parent.parent / ".env",          # backend/
    ]
    for c in candidates:
        if c.exists():
            return c
    return here.parent.parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_project_env()),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- Environment ----------
    ENVIRONMENT: str = "development"

    # ---------- Database ----------
    # If it does not start with postgres, we fall back to SQLite for dev.
    DATABASE_URL: str = "sqlite:///./carsoul_dev.db"

    # ---------- Redis ----------
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---------- Security ----------
    JWT_SECRET: str = "please-change-me-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ---------- AI / LLM ----------
    OPENAI_API_KEY: str = ""
    MODEL_NAME: str = "gpt-4o-mini"
    OPENAI_API_BASE: str = ""

    # ---------- Agent ----------
    AGENT_LANGUAGE: str = "zh-CN"
    AGENT_PROACTIVE: bool = True

    # ---------- CarSoul World Model (carModel) bridge ----------
    # Guardian 通过 HTTP 调用 carModel 车辆世界模型引擎，拿到真实的
    # SOH / 故障 / 残值 / 反事实预测。引擎默认跑在 :8000（见 start.sh）。
    CARSOUL_WORLD_API_URL: str = "http://localhost:8000"

    # ---------- Knowledge base ----------
    VECTOR_DB_PATH: str = "./ai-agent/memory/vector_store"
    CHROMA_COLLECTION: str = "carsoul_guardian"

    # ---------- CORS ----------
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT.lower() == "development"

    @property
    def effective_database_url(self) -> str:
        """Return a SQLAlchemy URL; force sqlite in dev if no PG available."""
        url = self.DATABASE_URL.strip()
        if url.startswith(("postgresql", "postgres+psycopg")):
            return url
        # Dev fallback: SQLite (file-based so data persists across reloads)
        if not url:
            return "sqlite:///./carsoul_dev.db"
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
