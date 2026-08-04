"""Declarative base for SQLAlchemy models.

All ORM models in `app.models` inherit from `Base`. TASK006 only ships the
base + connection; concrete business tables arrive in TASK007.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Project-wide declarative base."""

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        # Convert CamelCase -> snake_case for default table names.
        name = cls.__name__
        out = [name[0].lower()]
        for ch in name[1:]:
            out.append("_" + ch.lower() if ch.isupper() else ch)
        return "".join(out)
