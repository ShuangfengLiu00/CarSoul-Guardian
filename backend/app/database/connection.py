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


def _enable_sqlite_foreign_keys(dbapi_conn, _):
    """SQLite 外键约束**默认关闭**；必须在每次连接建立时显式开启。

    关键点（踩过坑）：`PRAGMA foreign_keys` 在事务内设置无效——python sqlite3
    默认会隐式开事务，所以在业务代码或 session 里 `execute("PRAGMA ...")` 不生效。
    只能在 `connect` 事件里、事务开启之前设置，写在连接建立那一刻才真正生效。

    按连接类型判断（而非按配置 URL），这样无论本监听器被挂到真实引擎还是
    测试用的临时引擎上，只要底层是 SQLite 连接就会生效；PostgreSQL 连接
    天然走原生外键强制，不会误执行 SQLite 专属的 PRAGMA。
    """
    import sqlite3

    if isinstance(dbapi_conn, sqlite3.Connection):
        cur = dbapi_conn.cursor()
        try:
            cur.execute("PRAGMA foreign_keys=ON")
        finally:
            cur.close()


if url.startswith("sqlite"):
    # 让 models 里那些 `ondelete="CASCADE"` 真正生效（否则默认关闭外键时
    # 它们只是摆设，用户删除车辆后关联快照/故障日志/行为数据变成孤儿行，
    # 直接违反 PIPL 删除权）。用 connect 事件挂接，确保每条新连接都开启。
    from sqlalchemy import event

    event.listen(engine, "connect", _enable_sqlite_foreign_keys)


def get_engine() -> Engine:
    """Return the singleton engine (useful for tests / scripts)."""
    return engine
