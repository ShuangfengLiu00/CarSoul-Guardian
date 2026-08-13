"""Orchestrator 总控调度器 — 意图识别 -> 分解 -> 路由 -> 聚合 -> 合规终审。
规则路由优先（WARN-02）LLM 兜底；串行链式深度 <= 2 步（R-01）；不继承 BaseAgent。"""
from __future__ import annotations

import concurrent.futures
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.compliance import COMPLIANCE_ACTIONS, compliance_hit
from app.kernel.actionstore_guardian import log_agent_event
from app.orchestrator.routing_table import (
    DISABLED_AGENT_REPLY, ENABLED_AGENTS, ROUTING_TABLE)

_MAX_SERIAL_STEPS = 2  # R-01: 串行链式深度硬上限


@dataclass
class IntentResult:
    """意图识别结果。mode: rule | llm | fallback。"""
    agent_name: str
    matched: bool = False
    score: int = 0
    disabled: bool = False
    mode: str = "fallback"


@dataclass
class SubTask:
    """分解后的子任务。depends_on 为前驱子任务索引（串行链）。"""
    agent_name: str
    input: str
    depends_on: Optional[int] = None


@dataclass
class OrchestratorResult:
    """Orchestrator 统一输出契约。"""
    answer: str
    status: str = "ok"  # ok | degraded | refused | clarify | failed
    agents_involved: list[str] = field(default_factory=list)
    execution_mode: str = "single"  # single | serial | parallel | none
    sub_results: list[dict] = field(default_factory=list)
    dispatch_log_id: str = ""
    caveats: list[str] = field(default_factory=list)
    confidence: Optional[float] = None


def _result_to_dict(r: AgentResult) -> dict:
    return {"agent": r.agent, "status": r.status, "answer": r.answer,
            "structured": r.structured, "latency_ms": r.latency_ms,
            "tool_calls": r.tool_calls}


class Orchestrator:
    """总控调度器。职责：意图识别 -> 分解 -> 路由 -> 聚合 -> 合规终审。"""

    def __init__(self, agents: Optional[dict[str, BaseAgent]] = None) -> None:
        self._agents: dict[str, BaseAgent] = agents or {}

    @property
    def registered_agents(self) -> list[str]:
        return list(self._agents.keys())

    def dispatch(self, user_message: str, user_id: str,
                 vehicle_id: Optional[str] = None) -> OrchestratorResult:
        t0 = time.perf_counter()
        log_id = uuid.uuid4().hex
        intent = self._identify_intent(user_message)
        # 阶段 2 禁用 Agent：命中关键词但 enabled=False
        if intent.matched and intent.disabled:
            res = OrchestratorResult(
                answer=DISABLED_AGENT_REPLY, status="clarify",
                agents_involved=[intent.agent_name], execution_mode="none",
                dispatch_log_id=log_id, caveats=["该功能将在阶段 2 上线"])
            return self._final_audit(res)
        # 未命中任何 Agent：给澄清引导
        if not intent.matched:
            res = OrchestratorResult(
                answer=("暂未理解您的意图。我可以帮您分析电池健康、驾驶安全、"
                        "充电优化等方面的问题，请试试更具体的提问。"),
                status="clarify", execution_mode="none", dispatch_log_id=log_id)
            return self._final_audit(res)
        subtasks = self._decompose(intent, user_message)
        if len(subtasks) == 1:
            results = [self._route_single(subtasks[0], user_id, log_id, vehicle_id)]
            mode = "single"
        elif self._has_serial_deps(subtasks):
            results = self._route_serial(subtasks, user_id, log_id, vehicle_id)
            mode = "serial"
        else:
            results = self._route_parallel(subtasks, user_id, log_id, vehicle_id)
            mode = "parallel"
        result = self._aggregate(results, log_id, mode)
        result = self._final_audit(result)
        self._audit_dispatch(log_id, user_id, user_message, intent, mode,
                             result, int((time.perf_counter() - t0) * 1000))
        return result

    def _identify_intent(self, user_message: str) -> IntentResult:
        """规则路由优先（WARN-02），LLM 兜底。"""
        msg = user_message.lower()
        best_name, best_score = "", 0
        for name, cfg in ROUTING_TABLE.items():
            if not cfg["enabled"]:
                continue
            score = sum(1 for kw in cfg["keywords"] if kw.lower() in msg)
            if score > best_score:
                best_score, best_name = score, name
        if best_score > 0:
            return IntentResult(best_name, matched=True, score=best_score,
                                mode="rule")
        for name, cfg in ROUTING_TABLE.items():  # 命中禁用 Agent 关键词
            if cfg["enabled"]:
                continue
            if any(kw.lower() in msg for kw in cfg["keywords"]):
                return IntentResult(name, matched=True, disabled=True, mode="rule")
        llm_name = self._llm_classify(user_message)  # LLM 兜底
        if llm_name:
            return IntentResult(llm_name, matched=True, mode="llm")
        return IntentResult("battery_health", matched=False, mode="fallback")

    def _llm_classify(self, user_message: str) -> str:
        """LLM 意图分类兜底。不可用/失败返回空串（调用方走 fallback）。"""
        try:
            from app.agents.llm_client import ChatMessage, LLMClient
            client = LLMClient()
            if not client.available:
                return ""
            options = ", ".join(ENABLED_AGENTS)
            sys_msg = (f"你是意图分类器。从以下选项选最匹配的：{options}。只返回选项名，无法判断返回 none。")
            out = client.generate(
                [ChatMessage("system", sys_msg), ChatMessage("user", user_message)],
                temperature=0.0, max_tokens=32).strip().lower()
            return out if out in ENABLED_AGENTS else ""
        except Exception:  # noqa: BLE001
            return ""

    def _decompose(self, intent: IntentResult,
                   user_message: str) -> list[SubTask]:
        primary = SubTask(agent_name=intent.agent_name, input=user_message)
        msg = user_message.lower()
        others = [name for name, cfg in ROUTING_TABLE.items()
                  if name != intent.agent_name and cfg["enabled"]
                  and any(kw.lower() in msg for kw in cfg["keywords"])]
        if not others:
            return [primary]
        subtasks = [primary, SubTask(agent_name=others[0],
                                     input=user_message, depends_on=0)]
        return subtasks[:_MAX_SERIAL_STEPS]  # R-01 截断

    @staticmethod
    def _has_serial_deps(subtasks: list[SubTask]) -> bool:
        return any(st.depends_on is not None for st in subtasks)

    def _build_ctx(self, subtask: SubTask, user_id: str, log_id: str,
                   upstream: Optional[dict] = None,
                   vehicle_id: Optional[str] = None) -> AgentContext:
        return AgentContext(query=subtask.input, session_id=user_id,
                            trace_id=log_id, slots={"user_id": user_id},
                            upstream=upstream or {}, vehicle_id=vehicle_id)

    def _route_single(self, subtask: SubTask, user_id: str,
                      log_id: str, vehicle_id: Optional[str] = None) -> AgentResult:
        return self._run_agent(subtask.agent_name,
                               self._build_ctx(subtask, user_id, log_id,
                                               vehicle_id=vehicle_id))

    def _route_serial(self, subtasks: list[SubTask], user_id: str,
                      log_id: str, vehicle_id: Optional[str] = None) -> list[AgentResult]:
        results: list[AgentResult] = []
        for st in subtasks:
            upstream: dict[str, Any] = {}
            if st.depends_on is not None and st.depends_on < len(results):
                prev = results[st.depends_on]
                upstream = {"answer": prev.answer, "status": prev.status,
                            "structured": prev.structured}
            results.append(self._run_agent(
                st.agent_name,
                self._build_ctx(st, user_id, log_id, upstream, vehicle_id)))
        return results

    def _route_parallel(self, subtasks: list[SubTask], user_id: str,
                        log_id: str, vehicle_id: Optional[str] = None) -> list[AgentResult]:
        # 并行扇出：用线程池并发执行同步 Agent。
        pairs = [(st.agent_name, self._build_ctx(st, user_id, log_id,
                                                 vehicle_id=vehicle_id))
                 for st in subtasks]
        ordered: list[Optional[AgentResult]] = [None] * len(pairs)
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=max(1, len(pairs))) as ex:
            futs = {ex.submit(self._run_agent, n, c): i
                    for i, (n, c) in enumerate(pairs)}
            for f in concurrent.futures.as_completed(futs):
                ordered[futs[f]] = f.result()
        return [r for r in ordered if r is not None]

    def _run_agent(self, name: str, ctx: AgentContext) -> AgentResult:
        agent = self._agents.get(name)
        if agent is None:
            return AgentResult(
                agent=name, status="degraded",
                answer=f"Agent '{name}' 尚未注册，暂无法处理该请求。",
                degraded_reason="agent_not_registered")
        return agent.run(ctx)

    def _aggregate(self, results: list[AgentResult], log_id: str,
                   mode: str) -> OrchestratorResult:
        if not results:
            return OrchestratorResult(answer="无可用结果", status="failed",
                                      dispatch_log_id=log_id, execution_mode=mode)
        if len(results) == 1:
            r = results[0]
            return OrchestratorResult(
                answer=r.answer, status=r.status, agents_involved=[r.agent],
                execution_mode=mode, sub_results=[_result_to_dict(r)],
                dispatch_log_id=log_id, caveats=list(r.caveats))
        parts, agents, caveats, worst = [], [], [], "ok"
        for r in results:
            agents.append(r.agent)
            parts.append(f"[{r.agent}] {r.answer}")
            caveats.extend(r.caveats)
            if r.status in ("failed", "refused", "degraded") and worst == "ok":
                worst = r.status
        return OrchestratorResult(
            answer="\n\n".join(parts), status=worst, agents_involved=agents,
            execution_mode=mode, sub_results=[_result_to_dict(r) for r in results],
            dispatch_log_id=log_id, caveats=caveats)

    def _final_audit(self, result: OrchestratorResult) -> OrchestratorResult:
        """Orchestrator 级合规终审：对聚合 answer 复检合规闸门。"""
        hit = compliance_hit(result.answer)
        if hit is not None:
            category, message = hit
            if COMPLIANCE_ACTIONS.get(category, "refuse") == "refuse":
                result.status = "refused"
                result.answer = message
                result.caveats.append(f"合规终审拦截：{category}")
        return result

    def _audit_dispatch(self, log_id: str, user_id: str, user_message: str,
                        intent: IntentResult, mode: str,
                        result: OrchestratorResult, duration_ms: int) -> None:
        try:
            log_agent_event(
                dispatch_id=log_id, agent_name="orchestrator",
                event_type="interaction",
                result={"user_id": user_id, "user_message": user_message,
                        "intent": intent.agent_name, "intent_mode": intent.mode,
                        "agents_involved": result.agents_involved,
                        "execution_mode": mode, "status": result.status,
                        "duration_ms": duration_ms})
        except Exception:  # noqa: BLE001 — 审计不得拖垮主链路
            pass
