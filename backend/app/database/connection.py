"""Database engine connection.

Creates the SQLAlchemy engine based on the effective DATABASE_URL. In dev
this transparently falls back to SQLite so the API can boot without a
running PostgreSQL instance.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import settings

_connect_args: dict = {}
_engine_kwargs: dict = {"pool_pre_ping": True}

url = settings.effective_database_url

# Normalise the PostgreSQL URL to whichever driver is installed.
# Bare "postgresql://" defaults to psycopg2; if only psycopg3 is present,
# rewrite to "postgresql+psycopg://" so SQLAlchemy picks it up.
if url.startswith("postgresql://"):
    try:
        import psycopg  # noqa: F401  (psycopg3)
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    except ImportError:
        pass  # fall back to psycopg2 dialect

if url.startswith("sqlite"):
    # SQLite needs these to work well with FastAPI threads.
    _connect_args = {"check_same_thread": False}
    _engine_kwargs.pop("pool_pre_ping", None)

engine: Engine = create_engine(url, connect_args=_connect_args, **_engine_kwargs)


def get_engine() -> Engine:
    """Return the singleton engine (useful for tests / scripts)."""
    return engine
