"""Database bridge — lets agent tools query the backend DB with Mock fallback.

The agent runs inside the backend process (loaded by ``agent_service``),
so it can import the backend's SQLAlchemy ``SessionLocal`` directly.
If the import fails (e.g. agent used standalone without backend), every
tool transparently falls back to its built-in Mock data.

Usage in a tool::

    from carsoul_agent.tools.db_helper import db_query

    def run(self, vehicle_id=1, **_):
        data = db_query(lambda db: self._fetch_from_db(db, vehicle_id))
        if data is not None:
            return ToolResult(ok=True, data=data)
        return self._mock_result(vehicle_id)
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Generator

import logging

_logger = logging.getLogger(__name__)

# Lazily resolved; stays None if backend is unavailable.
_SessionLocal = None  # type: ignore


def _resolve_session_factory():
    """Import the backend's SessionLocal on first use."""
    global _SessionLocal
    if _SessionLocal is not None:
        return _SessionLocal
    try:
        from app.database.session import SessionLocal  # type: ignore
        _SessionLocal = SessionLocal
        return _SessionLocal
    except Exception as exc:  # noqa: BLE001
        _logger.debug("Backend DB unavailable, tools will use Mock data: %s", exc)
        return None


@contextmanager
def get_db_session() -> Generator[Any, None, None]:
    """Yield a SQLAlchemy session, or None if the backend is unavailable."""
    factory = _resolve_session_factory()
    if factory is None:
        yield None
        return
    db = factory()
    try:
        yield db
    finally:
        db.close()


def db_query(fn: Callable[[Any], Any]) -> Any | None:
    """Run *fn* with a DB session.

    Returns ``fn(db)`` on success, or ``None`` if the backend is
    unavailable or *fn* raises.  Callers treat ``None`` as "use Mock".
    """
    factory = _resolve_session_factory()
    if factory is None:
        return None
    db = factory()
    try:
        return fn(db)
    except Exception as exc:  # noqa: BLE001
        _logger.debug("DB query failed, falling back to Mock: %s", exc)
        return None
    finally:
        db.close()
