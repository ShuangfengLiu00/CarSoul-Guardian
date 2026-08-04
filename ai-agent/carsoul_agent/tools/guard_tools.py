"""Guarded service tools — the *only* write-capable tools the Agent can call.

This file is the **tool-layer gate** mandated by the technical design's
"守护非控制" (guard-not-control) principle. The service sub-agent may
invoke exactly four write actions:

    1. push_reminder          — send a proactive reminder to the user
    2. record_lifecycle       — append a lifecycle event to the archive
    3. write_suggestion       — persist a service suggestion
    4. create_service_order   — create an external service order (P0-1)

There are **no actuator-control tools** here. Even if an LLM hallucinated
a ``/control/*`` call, the tool registry has no such entry to dispatch —
the boundary is enforced structurally, not by prompt etiquette.

A shared ``ActionStore`` collects every invocation so the full trace is
auditable (judges can inspect the store to verify "no control actions").
Actions are persisted to SQLite so the audit trail survives restarts.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from carsoul_agent.tools.base import BaseTool, ToolResult, default_registry


# ------------------------------------------------------------------ #
#  SQLite-backed audit store
# ------------------------------------------------------------------ #
_DEFAULT_DB_PATH = os.environ.get(
    "CARSOUL_AUDIT_DB",
    str(Path(__file__).resolve().parent.parent.parent.parent / "audit_store.db"),
)

_TABLE_SCHEMAS = {
    "reminders": """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            level TEXT,
            title TEXT,
            message TEXT,
            created_at TEXT
        )
    """,
    "lifecycle_events": """
        CREATE TABLE IF NOT EXISTS lifecycle_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            event_type TEXT,
            title TEXT,
            detail TEXT,
            recorded_at TEXT
        )
    """,
    "suggestions": """
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            priority TEXT,
            actions TEXT,
            explanation TEXT,
            written_at TEXT
        )
    """,
    "service_orders": """
        CREATE TABLE IF NOT EXISTS service_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            service_type TEXT,
            service_name TEXT,
            priority TEXT,
            reason TEXT,
            status TEXT,
            estimated_response TEXT,
            created_at TEXT
        )
    """,
}

_TABLE_FIELDS = {
    "reminders": ("vehicle_id", "level", "title", "message", "created_at"),
    "lifecycle_events": ("vehicle_id", "event_type", "title", "detail", "recorded_at"),
    "suggestions": ("vehicle_id", "priority", "actions", "explanation", "written_at"),
    "service_orders": (
        "vehicle_id", "service_type", "service_name", "priority",
        "reason", "status", "estimated_response", "created_at",
    ),
}


class ActionStore:
    """SQLite-persisted audit ledger of every guarded action.

    Every ``append`` writes through to SQLite immediately so the audit
    trail survives process restarts.  An in-memory mirror is kept for
    fast reads within the same process.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file.  Use ``:memory:`` for a
        purely in-memory store (testing only — no persistence).
    """

    def __init__(self, db_path: str = _DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        self._in_memory = db_path == ":memory:"

        # In-memory mirrors for fast reads.
        self.reminders: list[dict] = []
        self.lifecycle_events: list[dict] = []
        self.suggestions: list[dict] = []
        self.service_orders: list[dict] = []

        # Initialize SQLite tables.
        if not self._in_memory:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
        else:
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        for table, ddl in _TABLE_SCHEMAS.items():
            self._conn.execute(ddl)
        self._conn.commit()

    # -- internal helpers -------------------------------------------- #
    def _persist(self, table: str, record: dict[str, Any]) -> None:
        fields = _TABLE_FIELDS[table]
        values = [record.get(f) for f in fields]
        # JSON-encode list/dict fields (e.g. suggestions.actions).
        values = [
            json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
            for v in values
        ]
        placeholders = ", ".join("?" * len(fields))
        col_names = ", ".join(fields)
        self._conn.execute(
            f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})",
            values,
        )
        self._conn.commit()

    def _load_all(self, table: str) -> list[dict]:
        rows = self._conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
        result: list[dict] = []
        for row in rows:
            d = dict(row)
            # JSON-decode fields that look like JSON arrays/objects.
            for k, v in d.items():
                if isinstance(v, str) and v.startswith(("[", "{")):
                    try:
                        d[k] = json.loads(v)
                    except (json.JSONDecodeError, ValueError):
                        pass
            result.append(d)
        return result

    # -- public API -------------------------------------------------- #
    def append_reminder(self, record: dict) -> None:
        self.reminders.append(record)
        self._persist("reminders", record)

    def append_lifecycle_event(self, record: dict) -> None:
        self.lifecycle_events.append(record)
        self._persist("lifecycle_events", record)

    def append_suggestion(self, record: dict) -> None:
        self.suggestions.append(record)
        self._persist("suggestions", record)

    def append_service_order(self, record: dict) -> None:
        self.service_orders.append(record)
        self._persist("service_orders", record)

    def summary(self) -> dict[str, int]:
        return {
            "reminders": len(self.reminders),
            "lifecycle_events": len(self.lifecycle_events),
            "suggestions": len(self.suggestions),
            "service_orders": len(self.service_orders),
        }

    def reload(self) -> None:
        """Reload all records from SQLite into the in-memory mirrors."""
        self.reminders = self._load_all("reminders")
        self.lifecycle_events = self._load_all("lifecycle_events")
        self.suggestions = self._load_all("suggestions")
        self.service_orders = self._load_all("service_orders")

    def clear(self) -> None:
        self.reminders.clear()
        self.lifecycle_events.clear()
        self.suggestions.clear()
        self.service_orders.clear()
        for table in _TABLE_SCHEMAS:
            self._conn.execute(f"DELETE FROM {table}")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


# Shared singleton — the service agent and tools write here; the workflow
# reads it back to populate service_suggestion in the final state.
action_store = ActionStore()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------ #
class PushReminderTool(BaseTool):
    name = "push_reminder"
    description = (
        "向车主推送一条主动守护提醒（仅提醒，不执行任何车辆控制操作）。"
        "这是「守护非控制」红线下唯一允许的提醒工具。"
    )
    parameters = {
        "vehicle_id": "integer",
        "level": "string  # info | warning | urgent",
        "title": "string",
        "message": "string",
    }

    def run(
        self,
        vehicle_id: int = 1,
        level: str = "info",
        title: str = "",
        message: str = "",
        **_: Any,
    ) -> ToolResult:
        record = {
            "vehicle_id": vehicle_id,
            "level": level,
            "title": title,
            "message": message,
            "created_at": _now(),
        }
        action_store.append_reminder(record)
        return ToolResult(ok=True, data=record)


class RecordLifecycleEventTool(BaseTool):
    name = "record_lifecycle_event"
    description = (
        "向车辆数字生命档案追加一条生命周期事件记录"
        "（如守护介入、异常检出、建议采纳等），不修改车辆物理状态。"
    )
    parameters = {
        "vehicle_id": "integer",
        "event_type": "string  # guard_intervention | anomaly_detected | suggestion_adopted",
        "title": "string",
        "detail": "string",
    }

    def run(
        self,
        vehicle_id: int = 1,
        event_type: str = "guard_intervention",
        title: str = "",
        detail: str = "",
        **_: Any,
    ) -> ToolResult:
        record = {
            "vehicle_id": vehicle_id,
            "event_type": event_type,
            "title": title,
            "detail": detail,
            "recorded_at": _now(),
        }
        action_store.append_lifecycle_event(record)
        return ToolResult(ok=True, data=record)


class WriteServiceSuggestionTool(BaseTool):
    name = "write_service_suggestion"
    description = (
        "将守护引擎生成的服务建议持久化，供车主在档案中查阅与采纳。"
        "仅写入建议文本，不触发任何执行器。"
    )
    parameters = {
        "vehicle_id": "integer",
        "priority": "string  # high | medium | low",
        "actions": "array  # 可执行建议列表",
        "explanation": "string",
    }

    def run(
        self,
        vehicle_id: int = 1,
        priority: str = "medium",
        actions: list | None = None,
        explanation: str = "",
        **_: Any,
    ) -> ToolResult:
        record = {
            "vehicle_id": vehicle_id,
            "priority": priority,
            "actions": actions or [],
            "explanation": explanation,
            "written_at": _now(),
        }
        action_store.append_suggestion(record)
        return ToolResult(ok=True, data=record)


class CreateServiceOrderTool(BaseTool):
    name = "create_service_order"
    description = (
        "根据车主预授权，创建外部服务工单（道路救援/车企服务中心/保险服务）。"
        "这是三级升级闭环第三级的执行工具，仅创建工单，不直接调度服务。"
    )
    parameters = {
        "vehicle_id": "integer",
        "service_type": "string  # roadside_assist | manufacturer_service | insurance_service",
        "service_name": "string",
        "priority": "string  # high | medium | low",
        "reason": "string",
    }

    def run(
        self,
        vehicle_id: int = 1,
        service_type: str = "roadside_assist",
        service_name: str = "道路救援",
        priority: str = "high",
        reason: str = "",
        **_: Any,
    ) -> ToolResult:
        record = {
            "vehicle_id": vehicle_id,
            "service_type": service_type,
            "service_name": service_name,
            "priority": priority,
            "reason": reason,
            "status": "created",
            "estimated_response": "30分钟内",
            "created_at": _now(),
        }
        action_store.append_service_order(record)
        return ToolResult(ok=True, data=record)


# ------------------------------------------------------------------ #
# Registry — the canonical list of guarded write tools.
# Any new write capability MUST be added here; the service agent can
# only see tools registered in this set.
# ------------------------------------------------------------------ #
GUARDED_TOOLS = (
    PushReminderTool,
    RecordLifecycleEventTool,
    WriteServiceSuggestionTool,
    CreateServiceOrderTool,
)


def register_guarded_tools() -> None:
    """Register the three guarded tools into the default registry.

    Called on import so they are available to the service sub-agent.
    """
    for tool_cls in GUARDED_TOOLS:
        tool = tool_cls()
        if default_registry.get(tool.name) is None:
            default_registry.register(tool)


# Register on import.
register_guarded_tools()
