"""SQLite-backed persistent store for vehicle memories.

This module handles all database concerns so the engine layer can
operate purely on :class:`VehicleMemory` objects.  The store uses
Python's built-in ``sqlite3`` — zero external dependencies, zero
configuration, and the database is a single file that survives restarts.

Connection management
---------------------
Each :class:`MemoryStore` opens a single connection.  SQLite handles
concurrent reads natively; writes are serialised by the global
``write_lock``.  For the dev/demo single-process scenario this is more
than sufficient.  For multi-process deployments, switch to PostgreSQL
(a future V2 concern — the engine API stays the same).
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from kernel.memory_engine.models import VehicleMemory


_SCHEMA = """
CREATE TABLE IF NOT EXISTS vehicle_memories (
    id              TEXT PRIMARY KEY,
    vehicle_id      TEXT NOT NULL,
    occurred_at     TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    payload         TEXT,
    impact_target   TEXT,
    impact_delta    REAL,
    confidence      REAL,
    source          TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_mem_vehicle ON vehicle_memories(vehicle_id);",
    "CREATE INDEX IF NOT EXISTS idx_mem_occurred ON vehicle_memories(occurred_at);",
    "CREATE INDEX IF NOT EXISTS idx_mem_impact ON vehicle_memories(impact_target);",
    "CREATE INDEX IF NOT EXISTS idx_mem_type ON vehicle_memories(event_type);",
]


class MemoryStore:
    """SQLite persistent store for :class:`VehicleMemory` records.

    Parameters
    ----------
    db_url : str
        Connection string.  ``"sqlite:///path/to.db"`` for a file,
        ``"sqlite:///:memory:"`` for an in-memory database (testing).
    """

    def __init__(self, db_url: str = "sqlite:///carsoul.db") -> None:
        self._db_url = db_url
        self._write_lock = threading.Lock()
        self._conn = self._connect(db_url)
        self._init_schema()

    # ------------------------------------------------------------------ #
    #  Connection / schema
    # ------------------------------------------------------------------ #
    @staticmethod
    def _connect(db_url: str) -> sqlite3.Connection:
        """Parse the URL and open a SQLite connection."""
        if db_url.startswith("sqlite:///"):
            path = db_url[len("sqlite:///"):]
        elif db_url.startswith("sqlite://"):
            path = db_url[len("sqlite://"):]
        else:
            path = db_url

        if path == ":memory:":
            conn = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            # Ensure parent directory exists.
            db_path = Path(path)
            if db_path.parent and not db_path.parent.exists():
                db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(db_path), check_same_thread=False)

        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Create the table and indexes if they don't exist."""
        with self._write_lock:
            self._conn.executescript(_SCHEMA)
            for idx in _INDEXES:
                self._conn.execute(idx)
            self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        with self._write_lock:
            if self._conn:
                self._conn.close()
                self._conn = None  # type: ignore[assignment]

    # ------------------------------------------------------------------ #
    #  CRUD
    # ------------------------------------------------------------------ #
    def insert(self, memory: VehicleMemory) -> None:
        """Insert a single memory record."""
        with self._write_lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO vehicle_memories
                   (id, vehicle_id, occurred_at, event_type, payload,
                    impact_target, impact_delta, confidence, source, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                memory.to_db_row(),
            )
            self._conn.commit()

    def insert_many(self, memories: list[VehicleMemory]) -> int:
        """Batch-insert memory records. Returns the count inserted."""
        if not memories:
            return 0
        rows = [m.to_db_row() for m in memories]
        with self._write_lock:
            self._conn.executemany(
                """INSERT OR REPLACE INTO vehicle_memories
                   (id, vehicle_id, occurred_at, event_type, payload,
                    impact_target, impact_delta, confidence, source, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
            self._conn.commit()
        return len(rows)

    def get_by_id(self, memory_id: str) -> VehicleMemory | None:
        """Fetch a single memory by ID."""
        cur = self._conn.execute(
            "SELECT * FROM vehicle_memories WHERE id = ?", (memory_id,)
        )
        row = cur.fetchone()
        return VehicleMemory.from_db_row(tuple(row)) if row else None

    def recall(
        self,
        vehicle_id: str,
        topic: str | None = None,
        since: datetime | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[VehicleMemory]:
        """Query memories for a vehicle with optional filters.

        Parameters
        ----------
        vehicle_id : str
            The vehicle to query.
        topic : str, optional
            Filter by ``impact_target`` (e.g. ``"battery_stress"``).
            If ``None``, all topics are returned.
        since : datetime, optional
            Only memories that occurred at or after this time.
        event_type : str, optional
            Filter by event type.
        limit : int
            Maximum number of records to return (most recent first).
        """
        query = "SELECT * FROM vehicle_memories WHERE vehicle_id = ?"
        params: list[Any] = [vehicle_id]

        if topic is not None:
            query += " AND impact_target = ?"
            params.append(topic)
        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type)
        if since is not None:
            query += " AND occurred_at >= ?"
            params.append(since.isoformat())

        query += " ORDER BY occurred_at DESC LIMIT ?"
        params.append(limit)

        cur = self._conn.execute(query, params)
        return [VehicleMemory.from_db_row(tuple(row)) for row in cur.fetchall()]

    def count(self, vehicle_id: str | None = None) -> int:
        """Count memory records, optionally filtered by vehicle."""
        if vehicle_id is None:
            cur = self._conn.execute("SELECT COUNT(*) FROM vehicle_memories")
        else:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM vehicle_memories WHERE vehicle_id = ?",
                (vehicle_id,),
            )
        return cur.fetchone()[0]

    def topics(self, vehicle_id: str) -> list[str]:
        """Return distinct impact_target values for a vehicle."""
        cur = self._conn.execute(
            "SELECT DISTINCT impact_target FROM vehicle_memories "
            "WHERE vehicle_id = ? AND impact_target IS NOT NULL",
            (vehicle_id,),
        )
        return [row[0] for row in cur.fetchall()]

    def delete(self, memory_id: str) -> bool:
        """Delete a single memory by ID. Returns True if a row was deleted."""
        with self._write_lock:
            cur = self._conn.execute(
                "DELETE FROM vehicle_memories WHERE id = ?", (memory_id,)
            )
            self._conn.commit()
            return cur.rowcount > 0

    def delete_all(self, vehicle_id: str | None = None) -> int:
        """Delete memories, optionally filtered by vehicle. Returns count deleted."""
        with self._write_lock:
            if vehicle_id is None:
                cur = self._conn.execute("DELETE FROM vehicle_memories")
            else:
                cur = self._conn.execute(
                    "DELETE FROM vehicle_memories WHERE vehicle_id = ?",
                    (vehicle_id,),
                )
            self._conn.commit()
            return cur.rowcount
