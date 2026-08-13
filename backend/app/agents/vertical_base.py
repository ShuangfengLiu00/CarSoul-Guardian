"""垂直 Agent 共享底座 — 3 个 MVP 垂直 Agent 的公共父类。

继承 ``app.agents.base.BaseAgent``，补充 T3 契约所需的横切能力：
  * 经 carModel 网关调用工具，并**保留** ``data_source`` / ``model_grade``
    （``BaseAgent.call_tool_http`` 会丢弃 ``data_source``，这里重写补齐，
    用于透传 data_source 并推导 confidence，满足「返回含 data_source +
    confidence 的 AgentResult」）。
  * 车辆 id 解析：ctx.vehicle_id -> 配置默认 -> 无则澄清（绝不拿一辆随机车冒充本车）。
  * data_source -> confidence 映射（与 ``ExternalServiceAdapter`` 口径一致）。
  * 友好的降级 / 失败封装（**不编造**车况）。

TD-01 硬约束：只走 HTTP 调 carModel 网关（``/gateway/execute``），
禁止进程内 import api.main / carModel 任意模块。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.core.config import settings

# data_source -> confidence（与 ExternalServiceAdapter 口径一致）
_DATA_SOURCE_CONFIDENCE = {
    "live": 0.92,
    "live_partial": 0.80,
    "cached": 0.75,
    "mock": 0.45,
    "unavailable": 0.0,
}
# data_source 严重度（取最差者决定整体降级）
_SOURCE_RANK = {
    "live": 3,
    "live_partial": 3,
    "cached": 2,
    "mock": 1,
    "unavailable": 0,
}


def soh_to_pct(value: Any) -> Optional[float]:
    """把 SOH 统一成百分数（0–1 量纲自动 ×100）。

    carModel 返回的是 0–1 浮点（0.923），这里统一为人读百分数 92.3。
    已大于 1 的值视为已是百分数，原样保留。
    """
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v <= 1.0:
        return round(v * 100, 1)
    return round(v, 1)


def worst_source(*sources: Optional[str]) -> str:
    """取多个 data_source 中最差的一个。"""
    ranked = [( _SOURCE_RANK.get((s or "").lower(), 0), s) for s in sources if s]
    if not ranked:
        return "unavailable"
    return min(ranked, key=lambda kv: kv[0])[1]


class VerticalAgentBase(BaseAgent):
    """3 个 MVP 垂直 Agent 的共享底座。子类声明 ``name`` / ``domain`` / ``tools``。"""

    # ── 车辆解析 ──
    def resolve_vehicle_id(self, ctx: AgentContext) -> Optional[str]:
        """ctx.vehicle_id -> 配置默认 -> None（不冒充本车）。"""
        if ctx.vehicle_id:
            return ctx.vehicle_id
        default = getattr(settings, "CARSOUL_WORLD_DEFAULT_VEHICLE_ID", "") or ""
        return default or None

    # ── confidence ──
    def confidence_from_source(self, data_source: Optional[str], *,
                               fallback: float = 0.9) -> float:
        return _DATA_SOURCE_CONFIDENCE.get((data_source or "").lower(), fallback)

    # ── 工具调用（保留 data_source）──
    def call_tool(self, tool_name: str, args: dict, ctx: AgentContext) -> dict:
        """经 carModel 网关调用工具，返回含 data_source / confidence 的富结果。

        相对 ``BaseAgent.call_tool_http`` 的唯一差异：保留 carModel 信封里的
        ``data_source`` / ``model_grade``，并据此推导 ``confidence``，其余行为
        完全一致（含工具白名单校验、HTTP 传输、异常转结构化错误、不抛）。
        """
        if tool_name not in self.tools:
            return {"error": "not_in_agent_whitelist", "tool": tool_name,
                    "status": "rejected", "data_source": "unavailable",
                    "confidence": 0.0}
        t0 = time.perf_counter()
        try:
            base = settings.CARSOUL_WORLD_API_URL.rstrip("/")
            url = f"{base}/gateway/execute"
            payload = {
                "tool_name": tool_name,
                "args": args,
                "vehicle_id": ctx.vehicle_id or "",
                "session_id": ctx.session_id,
            }
            headers = {"Content-Type": "application/json"}
            token = settings.CARSOUL_WORLD_API_TOKEN
            if token:
                headers["Authorization"] = f"Bearer {token}"
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            latency = int((time.perf_counter() - t0) * 1000)
            status = result.get("status", "unknown")
            ds = result.get("data_source", "live")
            if status == "success":
                return {
                    "status": "success",
                    "data": result.get("data"),
                    "data_source": ds,
                    "confidence": self.confidence_from_source(ds),
                    "latency_ms": latency,
                    "tool": tool_name,
                    "trace_id": result.get("trace_id", ""),
                    "model_grade": result.get("model_grade"),
                }
            # rejected / degraded / failed / timeout / unknown
            return {
                "error": status,
                "tool": tool_name,
                "msg": result.get("degraded_reason", "")
                or result.get("detail", ""),
                "data_source": ds,
                "data": result.get("data"),
                "confidence": self.confidence_from_source(ds, fallback=0.0),
                "latency_ms": latency,
            }
        except Exception as e:  # noqa: BLE001 — 边界：任何异常都转结构化错误
            latency = int((time.perf_counter() - t0) * 1000)
            return {
                "error": "http_failed",
                "tool": tool_name,
                "msg": f"{type(e).__name__}: {e}",
                "data_source": "unavailable",
                "confidence": 0.0,
                "latency_ms": latency,
            }

    # ── 结果组装辅助 ──
    @staticmethod
    def tool_call_entry(r: dict) -> dict:
        """把一次 call_tool 结果压成审计用的 tool_calls 条目。"""
        return {
            "tool": r.get("tool"),
            "status": r.get("status", "error" if r.get("error") else "unknown"),
            "data_source": r.get("data_source"),
            "latency_ms": r.get("latency_ms", 0),
            "error": r.get("error"),
        }

    def degrade_result(self, vehicle_id: str, call_result: dict,
                       label: str) -> AgentResult:
        """工具调用失败/降级时的一致化封装：友好提示，不编造车况。"""
        reason = (call_result.get("msg")
                  or call_result.get("error") or "unknown")
        answer = (
            f"暂时无法获取{label}数据（原因：{reason}）。"
            f"可能 carModel 预测引擎未启动，或车辆 {vehicle_id} 的历史数据不足 180 天。"
            "请稍后重试，或确认预测引擎已就绪后再试。"
        )
        return AgentResult(
            agent=self.name,
            status="degraded",
            answer=answer,
            degraded_reason=reason,
            caveats=["数据暂不可用，以上为占位说明而非车况结论"],
            tool_calls=[self.tool_call_entry(call_result)],
        )

    def no_vehicle_result(self) -> AgentResult:
        """会话未绑定具体车辆时的澄清回复（绝不拿随机车冒充本车）。"""
        return AgentResult(
            agent=self.name,
            status="clarify",
            answer=("当前会话未绑定具体车辆，无法查询该车车况。"
                    "请在车辆档案中选择本车，或提供车辆编号后重试。"),
        )
