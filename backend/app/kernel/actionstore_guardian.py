"""Guardian Agent 审计账本 — 哈希链防篡改（TD-01 新建）。

从 BaseAgent._audit 调用，记录 Agent 运行事件：
  dispatch_id / agent_name / event_type / tool_name / result(json) / audit_hash / created_at

哈希链：每条事件的 audit_hash = SHA-256(prev_hash + 事件字段)，
篡改任意一条记录会导致后续所有哈希校验失败。

审计写入异常不得拖垮主链路——log_agent_event 内部捕获所有异常，
失败时返回空串（调用方可忽略返回值）。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_LOCK = threading.Lock()

_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "actionstore_guardian.db"
_INITED = False


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_audit_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            dispatch_id TEXT    NOT NULL,
            agent_name  TEXT    NOT NULL,
            event_type  TEXT    NOT NULL,
            tool_name   TEXT    NOT NULL DEFAULT '',
            result      TEXT    NOT NULL DEFAULT '{}',
            audit_hash  TEXT    NOT NULL,
            created_at  TEXT    NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_dispatch ON agent_audit_events(dispatch_id)"
    )
    conn.commit()


def _get_conn() -> sqlite3.Connection:
    global _INITED
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), timeout=5)
    if not _INITED:
        _ensure_table(conn)
        _INITED = True
    return conn


def _last_hash(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT audit_hash FROM agent_audit_events ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else "GENESIS"


def log_agent_event(
    *,
    dispatch_id: str,
    agent_name: str,
    event_type: str,
    tool_name: str = "",
    result: Optional[dict[str, Any]] = None,
    vehicle_id: str = "",
    session_id: str = "",
) -> str:
    """记录一条 Agent 审计事件，返回 audit_hash（失败返回空串）。

    参数：
      dispatch_id : 调度 ID（一次 Agent run 的唯一标识）
      agent_name  : Agent 名称
      event_type  : interaction / model-call / warning
      tool_name   : 工具名（interaction/warning 为空）
      result      : 结果字典（JSON 序列化存储）
      vehicle_id  : 车辆 ID（可选，写入 result 中）
      session_id  : 会话 ID（可选，写入 result 中）

    线程安全：内部加锁，避免并发写入冲突。
    异常安全：任何异常都捕获并返回空串，不拖垮主链路。
    """
    try:
        result_dict = dict(result or {})
        if vehicle_id:
            result_dict.setdefault("vehicle_id", vehicle_id)
        if session_id:
            result_dict.setdefault("session_id", session_id)
        result_json = json.dumps(result_dict, ensure_ascii=False, sort_keys=True)
        created_at = datetime.now(timezone.utc).isoformat()

        with _LOCK:
            conn = _get_conn()
            try:
                prev = _last_hash(conn)
                raw = f"{prev}|{dispatch_id}|{agent_name}|{event_type}|{tool_name}|{result_json}|{created_at}"
                audit_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                conn.execute(
                    """
                    INSERT INTO agent_audit_events
                        (dispatch_id, agent_name, event_type, tool_name,
                         result, audit_hash, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (dispatch_id, agent_name, event_type, tool_name,
                     result_json, audit_hash, created_at),
                )
                conn.commit()
                return audit_hash
            finally:
                conn.close()
    except Exception:  # noqa: BLE001 — 审计不得拖垮主链路
        return ""


def log_external_call(*, service_name: str, method: str,
                      params: dict[str, Any]) -> str:
    """记录外部服务调用发起。返回 audit_hash（失败返回空串）。

    仅记录参数键名（不记值），避免泄露敏感数据。
    复用 log_agent_event 的哈希链，dispatch_id 格式 ext:<service>。
    """
    safe = {k: type(v).__name__ for k, v in (params or {}).items()}
    return log_agent_event(
        dispatch_id=f"ext:{service_name}",
        agent_name=service_name,
        event_type="interaction",
        tool_name=method,
        result={"phase": "call", "param_keys": list(safe.keys())},
    )


def log_external_result(*, service_name: str, method: str,
                        result: dict[str, Any], data_source: str,
                        confidence: float, latency_ms: int) -> str:
    """记录外部服务调用结果。返回 audit_hash（失败返回空串）。

    仅记录元数据（data_source/confidence/latency），不记原始结果载荷。
    复用 log_agent_event 的哈希链。
    """
    return log_agent_event(
        dispatch_id=f"ext:{service_name}",
        agent_name=service_name,
        event_type="model-call",
        tool_name=method,
        result={
            "phase": "result",
            "data_source": data_source,
            "confidence": confidence,
            "latency_ms": latency_ms,
        },
    )


def verify_chain() -> bool:
    """校验哈希链完整性（供审计验收用）。返回 True 表示链未断裂。"""
    try:
        with _LOCK:
            conn = _get_conn()
            try:
                rows = conn.execute(
                    "SELECT dispatch_id, agent_name, event_type, tool_name, "
                    "result, audit_hash, created_at FROM agent_audit_events ORDER BY id"
                ).fetchall()
                prev = "GENESIS"
                for r in rows:
                    dispatch_id, agent_name, event_type, tool_name, \
                        result_json, audit_hash, created_at = r
                    raw = f"{prev}|{dispatch_id}|{agent_name}|{event_type}|{tool_name}|{result_json}|{created_at}"
                    expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()
                    if expected != audit_hash:
                        return False
                    prev = audit_hash
                return True
            finally:
                conn.close()
    except Exception:  # noqa: BLE001
        return False
