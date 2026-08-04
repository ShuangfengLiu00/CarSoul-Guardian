"""User model.

Full account/profile design with preferences and agent settings.
TASK009 will add role-based access control; for now a simple role string
suffices for the digital-life archive.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database.base import Base

JSONType = SQLiteJSON().with_variant(JSON(), "postgresql")


class User(Base):
    """A registered CarSoul Guardian user / vehicle owner."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))

    # ---- Profile ----
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ---- Role / permissions ----
    role: Mapped[str] = mapped_column(String(32), default="owner")
    # owner | admin | mechanic | agent

    # ---- Flexible preferences ----
    preferences: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )  # {theme, language, notification_settings, …}
    agent_settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSONType, nullable=True
    )  # {proactive, language, persona, …}

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
