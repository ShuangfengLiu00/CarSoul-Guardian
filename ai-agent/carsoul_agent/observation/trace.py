"""Trace Collector — 全链路追踪（含 Token 消耗）.

Implements the trace-collection component of the Agent Observation
Layer (架构第四层). Every Agent invocation — from user request →
Manager → calling chain → Skill → result generation — is recorded
as an ordered chain of ``TraceRecord`` entries, each carrying token
usage and timing data so the entire reasoning chain is replayable
and cost-auditable ("推理可追溯 + 成本可审计").

This complements the lightweight ``trace_log`` embedded in
``AgentState`` (``agents/core/state.py``) with a richer, queryable,
fleet-wide trace store that also feeds the Evaluation and
Optimization loops.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TraceRecord:
    """A single step within a trace chain.

    Mirrors the step vocabulary defined by ``Trace`` in
    ``agents/core/state.py`` (PERCEIVE / UNDERSTAND / REASON / TOOL /
    ACT / NORMAL) but adds token-consumption and timing fields for
    cost analysis.
    """

    trace_id: str
    workflow_id: str
    agent_id: str
    step: str  # PERCEIVE/UNDERSTAND/REASON/TOOL/ACT
    timestamp: str
    detail: str
    duration_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for API responses / persistence."""
        return {
            "trace_id": self.trace_id,
            "workflow_id": self.workflow_id,
            "agent_id": self.agent_id,
            "step": self.step,
            "timestamp": self.timestamp,
            "detail": self.detail,
            "duration_ms": self.duration_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "data": self.data,
        }


class TraceCollector:
    """全链路追踪收集器.

    Records the complete chain of a user request → Manager → calling
    chain → Skill → result generation. Each trace is identified by a
    ``trace_id`` and contains an ordered list of ``TraceRecord``
    steps plus aggregated token / timing statistics.
    """

    def __init__(self) -> None:
        # trace_id → trace envelope dict
        self._traces: dict[str, dict[str, Any]] = {}
        # insertion order for "recent" queries
        self._order: list[str] = []
        self._max_traces: int = 1000

    # ------------------------------------------------------------------
    #  Trace lifecycle
    # ------------------------------------------------------------------
    def start_trace(self, workflow_id: str, user_message: str) -> str:
        """创建一条新追踪，返回 trace_id."""
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        self._traces[trace_id] = {
            "trace_id": trace_id,
            "workflow_id": workflow_id,
            "user_message": user_message,
            "started_at": now,
            "completed_at": None,
            "steps": [],
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "total_duration_ms": 0.0,
        }
        self._order.append(trace_id)
        # evict oldest trace when over capacity (ring-buffer style)
        while len(self._order) > self._max_traces:
            old_id = self._order.pop(0)
            self._traces.pop(old_id, None)
        logger.debug("Trace started: %s (workflow=%s)", trace_id, workflow_id)
        return trace_id

    def record_step(
        self,
        trace_id: str,
        agent_id: str,
        step: str,
        detail: str,
        **kwargs: Any,
    ) -> None:
        """向已有追踪追加一个步骤记录.

        Keyword args may include ``duration_ms``, ``prompt_tokens``,
        ``completion_tokens``, ``total_tokens`` and ``data``.
        """
        trace = self._traces.get(trace_id)
        if trace is None:
            logger.warning("record_step: unknown trace_id '%s'", trace_id)
            return
        prompt_tokens = int(kwargs.get("prompt_tokens", 0))
        completion_tokens = int(kwargs.get("completion_tokens", 0))
        total_tokens = int(kwargs.get("total_tokens", 0))
        # auto-compute total_tokens when only parts are supplied
        if total_tokens == 0 and (prompt_tokens or completion_tokens):
            total_tokens = prompt_tokens + completion_tokens
        record = TraceRecord(
            trace_id=trace_id,
            workflow_id=trace["workflow_id"],
            agent_id=agent_id,
            step=step,
            timestamp=datetime.now(timezone.utc).isoformat(),
            detail=detail,
            duration_ms=float(kwargs.get("duration_ms", 0.0)),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            data=kwargs.get("data", {}) or {},
        )
        trace["steps"].append(record)
        trace["total_prompt_tokens"] += prompt_tokens
        trace["total_completion_tokens"] += completion_tokens
        trace["total_tokens"] += total_tokens
        trace["total_duration_ms"] += record.duration_ms

    def record_token_usage(
        self,
        trace_id: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """将 Token 用量记到该追踪最近一步（并累加到追踪汇总）."""
        trace = self._traces.get(trace_id)
        if trace is None or not trace["steps"]:
            logger.warning("record_token_usage: no step for trace '%s'", trace_id)
            return
        record: TraceRecord = trace["steps"][-1]
        record.prompt_tokens += prompt_tokens
        record.completion_tokens += completion_tokens
        record.total_tokens = record.prompt_tokens + record.completion_tokens
        trace["total_prompt_tokens"] += prompt_tokens
        trace["total_completion_tokens"] += completion_tokens
        trace["total_tokens"] += prompt_tokens + completion_tokens

    def record_timing(self, trace_id: str, duration_ms: float) -> None:
        """将耗时记到该追踪最近一步（并累加到追踪汇总）."""
        trace = self._traces.get(trace_id)
        if trace is None or not trace["steps"]:
            logger.warning("record_timing: no step for trace '%s'", trace_id)
            return
        record: TraceRecord = trace["steps"][-1]
        record.duration_ms += duration_ms
        trace["total_duration_ms"] += duration_ms

    def complete_trace(self, trace_id: str) -> None:
        """标记一条追踪完成."""
        trace = self._traces.get(trace_id)
        if trace is None:
            return
        trace["completed_at"] = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    #  Query
    # ------------------------------------------------------------------
    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """返回完整追踪（含每一步的序列化记录）."""
        trace = self._traces.get(trace_id)
        if trace is None:
            return None
        return self._serialise_trace(trace)

    def get_recent_traces(self, limit: int = 20) -> list[dict[str, Any]]:
        """返回最近的追踪（newest first）."""
        ids = self._order[-limit:]
        return [
            self._serialise_trace(self._traces[tid])
            for tid in reversed(ids)
            if tid in self._traces
        ]

    def get_token_stats(self) -> dict[str, Any]:
        """返回 Token 统计：总量 / 平均 / 按 agent 分桶."""
        total_prompt = 0
        total_completion = 0
        total_tokens = 0
        per_agent: dict[str, dict[str, int]] = {}
        trace_count = 0
        for trace in self._traces.values():
            trace_count += 1
            total_prompt += trace["total_prompt_tokens"]
            total_completion += trace["total_completion_tokens"]
            total_tokens += trace["total_tokens"]
            for record in trace["steps"]:
                bucket = per_agent.setdefault(
                    record.agent_id,
                    {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                        "steps": 0,
                    },
                )
                bucket["prompt_tokens"] += record.prompt_tokens
                bucket["completion_tokens"] += record.completion_tokens
                bucket["total_tokens"] += record.total_tokens
                bucket["steps"] += 1
        return {
            "trace_count": trace_count,
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "avg_tokens_per_trace": round(total_tokens / trace_count, 2) if trace_count else 0.0,
            "per_agent": per_agent,
        }

    # ------------------------------------------------------------------
    #  Serialisation
    # ------------------------------------------------------------------
    @staticmethod
    def _serialise_trace(trace: dict[str, Any]) -> dict[str, Any]:
        return {
            "trace_id": trace["trace_id"],
            "workflow_id": trace["workflow_id"],
            "user_message": trace["user_message"],
            "started_at": trace["started_at"],
            "completed_at": trace["completed_at"],
            "step_count": len(trace["steps"]),
            "total_prompt_tokens": trace["total_prompt_tokens"],
            "total_completion_tokens": trace["total_completion_tokens"],
            "total_tokens": trace["total_tokens"],
            "total_duration_ms": round(trace["total_duration_ms"], 2),
            "steps": [r.to_dict() for r in trace["steps"]],
        }

    def to_dict(self) -> dict[str, Any]:
        """整体快照（用于前端观测面板）."""
        return {
            "trace_count": len(self._traces),
            "recent": self.get_recent_traces(limit=10),
            "token_stats": self.get_token_stats(),
        }


# Singleton instance.
trace_collector = TraceCollector()
