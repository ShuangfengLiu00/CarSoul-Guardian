"""BaseAgent — 从 carModel agent/base.py 迁移并改造（TD-01）。

模板方法 run(): parse -> gate -> execute -> audit
改造：call_tool_http HTTP POST carModel 网关（不再进程内调用）；
_gate 调用本地 compliance；_audit 调用 kernel.actionstore_guardian。
P-02：AgentResult 不含 control 字段（Guardian 非控制）。
"""
from __future__ import annotations

import json
import time
import uuid
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from app.agents.compliance import (
    compliance_hit, COMPLIANCE_ACTIONS, HARD_REFUSE_CATEGORIES)
from app.kernel.actionstore_guardian import log_agent_event


@dataclass
class AgentContext:
    """跨 Agent 传递的上下文。子类只读取自己声明的字段。"""
    query: str
    session_id: str = ""
    trace_id: str = ""
    vehicle_id: Optional[str] = None
    role: str = "owner"
    intent: Optional[str] = None
    slots: dict[str, Any] = field(default_factory=dict)
    upstream: dict[str, Any] = field(default_factory=dict)
    budget_ms: int = 1500


@dataclass
class AgentResult:
    """Agent 输出契约。P-02：不含 control 字段（Guardian 非控制）。"""
    agent: str
    status: Literal["ok", "degraded", "refused", "clarify", "failed"]
    answer: str
    structured: dict[str, Any] = field(default_factory=dict)
    actions: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    degraded_reason: Optional[str] = None
    latency_ms: int = 0
    compliance_category: Optional[str] = None
    compliance_action: Optional[str] = None


_STATUS_MAP = {
    "ok": "success", "degraded": "degraded", "refused": "rejected",
    "clarify": "success", "failed": "failed",
}


class BaseAgent:
    """所有垂直 Agent 的基类。子类实现 parse()/execute()，声明 name/domain/tools。"""

    name: str = "base"
    domain: str = ""
    tools: list[str] = []

    def run(self, ctx: AgentContext) -> AgentResult:
        """模板方法：parse -> gate -> execute -> audit。"""
        t0 = time.perf_counter()
        dispatch_id = ctx.trace_id or uuid.uuid4().hex
        parsed = self.parse(ctx)
        gate_result = self._gate(ctx)
        if gate_result is not None:
            gate_result.latency_ms = int((time.perf_counter() - t0) * 1000)
            self._audit(ctx, gate_result, dispatch_id)
            return gate_result
        try:
            result = self.execute(ctx, parsed)
        except Exception as e:  # noqa: BLE001
            result = AgentResult(
                agent=self.name, status="failed",
                answer=f"Agent 执行异常：{type(e).__name__}: {e}",
                degraded_reason=str(e),
            )
        result.latency_ms = int((time.perf_counter() - t0) * 1000)
        self._audit(ctx, result, dispatch_id)
        return result

    def parse(self, ctx: AgentContext) -> dict[str, Any]:
        """解析上下文。子类可覆盖。默认透传 query。"""
        return {"query": ctx.query}

    def execute(self, ctx: AgentContext, parsed: dict[str, Any]) -> AgentResult:
        raise NotImplementedError(f"{self.name} 未实现 execute()")

    def _gate(self, ctx: AgentContext) -> Optional[AgentResult]:
        """合规闸门（第 0 步红线）。命中返回短路结果，未命中返回 None。

        identity/geo/data_fraud/repair_mislead -> refused（硬拒答）
        safety_critical -> ok + 免责文案（短路但不标 refused）
        """
        hit = compliance_hit(ctx.query)
        if hit is None:
            return None
        category, message = hit
        action = COMPLIANCE_ACTIONS.get(category, "refuse")
        if category in HARD_REFUSE_CATEGORIES:
            return AgentResult(
                agent=self.name, status="refused", answer=message,
                compliance_category=category, compliance_action=action,
            )
        return AgentResult(
            agent=self.name, status="ok", answer=message,
            caveats=["安全结论免责：不替代专业检修"],
            compliance_category=category, compliance_action=action,
        )

    def call_tool_http(
        self, tool_name: str, args: dict[str, Any], ctx: AgentContext
    ) -> dict[str, Any]:
        """HTTP POST carModel /gateway/execute。越界/异常返回结构化错误，不抛。

        1. Agent 白名单（self.tools）越界 -> not_in_agent_whitelist
        2. carModel 网关返回 ToolResult 信封（success/degraded/failed/rejected）
        """
        if tool_name not in self.tools:
            return {"error": "not_in_agent_whitelist", "tool": tool_name}
        t0 = time.perf_counter()
        try:
            from app.core.config import settings
            base = settings.CARSOUL_WORLD_API_URL.rstrip("/")
            url = f"{base}/gateway/execute"
            payload = {"tool_name": tool_name, "args": args,
                       "vehicle_id": ctx.vehicle_id or "",
                       "session_id": ctx.session_id}
            headers = {"Content-Type": "application/json"}
            token = settings.CARSOUL_WORLD_API_TOKEN
            if token:
                headers["Authorization"] = f"Bearer {token}"
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            latency = int((time.perf_counter() - t0) * 1000)
            if result.get("status") == "success":
                return {"data": result.get("data"), "latency_ms": latency,
                        "status": "success", "tool": tool_name,
                        "trace_id": result.get("trace_id", "")}
            return {"error": result.get("status", "unknown"), "tool": tool_name,
                    "msg": result.get("degraded_reason", ""),
                    "latency_ms": latency, "data": result.get("data")}
        except Exception as e:  # noqa: BLE001
            latency = int((time.perf_counter() - t0) * 1000)
            return {"error": "http_failed", "tool": tool_name,
                    "msg": f"{type(e).__name__}: {e}", "latency_ms": latency}

    def _audit(self, ctx: AgentContext, result: AgentResult,
               dispatch_id: str) -> None:
        """写审计事件（interaction/model-call/warning）。异常不得拖垮主链路。"""
        try:
            log_agent_event(
                dispatch_id=dispatch_id, agent_name=result.agent,
                event_type="interaction", tool_name="",
                result={"status": _STATUS_MAP.get(result.status, ""),
                        "compliance_category": result.compliance_category,
                        "degraded_reason": result.degraded_reason,
                        "latency_ms": result.latency_ms},
            )
            for tc in result.tool_calls:
                log_agent_event(
                    dispatch_id=dispatch_id, agent_name=self.name,
                    event_type="model-call", tool_name=tc.get("tool", ""),
                    result={"status": tc.get("status", ""),
                            "error": tc.get("error"),
                            "latency_ms": tc.get("latency_ms", 0)},
                )
            if result.status in ("refused", "degraded", "failed"):
                log_agent_event(
                    dispatch_id=dispatch_id, agent_name=result.agent,
                    event_type="warning", tool_name="",
                    result={"warning_type": result.status,
                            "compliance_category": result.compliance_category,
                            "degraded_reason": result.degraded_reason},
                )
        except Exception:  # noqa: BLE001
            pass
