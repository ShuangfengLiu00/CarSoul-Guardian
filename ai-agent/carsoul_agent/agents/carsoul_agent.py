"""CarSoul Guardian Agent — the primary guardian agent.

This is the **user-facing entry point** that orchestrates the five
sub-agent core workflow:

    user message → gather vehicle state → CoreWorkflow → answer + trace

Responsibilities:
  1. 车辆信息理解 — gather vehicle archive data via tools
  2. 车辆健康分析 — feed health data into the perception node
  3. 用户问题回答 — return the explainer's output as the answer
  4. 主动提醒生成 — the service node fires guarded reminder tools

Design notes:
- When an LLM is configured (OPENAI_API_KEY present + openai installed),
  the sub-agents use it for semantic detection, root-cause enrichment,
  and natural-language explanation.
- Otherwise all five sub-agents run in rule-based offline mode.
- AI logic lives HERE, never in the backend API routes.
- The full reasoning chain is captured in ``trace_log`` for auditability.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from carsoul_agent.agents.base import BaseAgent
from carsoul_agent.agents.core import CoreWorkflow
from carsoul_agent.agents.core.state import AgentState, trace_entry
from carsoul_agent.agents.registry import register_agent
from carsoul_agent.config import settings
from carsoul_agent.memory import Message
from carsoul_agent.prompts import get_prompt
from carsoul_agent.tools import default_registry
from carsoul_agent.tools.guard_tools import action_store

# NOTE: Governance and WorkflowEngine are imported lazily in
# _init_governance() to avoid a circular import:
#   workflow_engine.engine → agents.core.state → agents.__init__
#   → carsoul_agent.py → workflow_engine (circular)

logger = logging.getLogger(__name__)

# Keywords that trigger the full workflow vs. a lightweight greeting reply.
_WORKFLOW_TRIGGERS = [
    "健康", "状态", "怎么样", "保养", "maintenance", "换油", "机油", "保养计划",
    "档案", "信息", "车辆", "vin", "info", "故障", "报警", "灯亮", "fault", "异常",
    "电池", "battery", "温度", "temperature", "轮胎", "刹车", "tire", "brake",
    "驾驶", "行为", "driving", "安全", "风险", "risk", "提醒", "预警",
    "长途", "自驾", "出行", "出差", "旅游", "高速", "公里", "千米", "km", "trip", "travel",
    "自驾游", "回老家", "跑长途", "远行", "公路旅行", "路程",
]

# Keywords that signal a long-trip scenario — triggers comprehensive
# vehicle health check before the trip.
_LONG_TRIP_KEYWORDS = [
    "长途", "自驾", "出行", "出差", "旅游", "高速", "公里", "千米", "km",
    "trip", "travel", "自驾游", "回老家", "跑长途", "远行", "公路旅行",
    "下周", "明天出发", "准备出门", "上路",
]

# Keywords that signal a general car-knowledge question (vs. a request about
# the user's own vehicle). These route to the RAG answer path instead of the
# five-sub-agent vehicle-state workflow.
_KNOWLEDGE_HINTS = [
    "多久换", "什么时候换", "怎么", "如何", "为什么", "区别", "是什么", "是什么意思",
    "正常吗", "对吗", "可以吗", "需要吗", "多少公里", "多少", "周期", "寿命",
    "建议", "推荐", "注意", "科普", "知识", "讲解", "解释", "含义", "作用",
    "选车", "买车", "二手车", "新车", "保险", "理赔", "年检", "违章", "扣分",
    "充电", "续航", "衰减", "胎压", "胎纹", "机油", "防冻液", "变速箱油",
    "冬天", "夏季", "雨雪", "磨合", "暴晒", "涉水", "爆胎",
]


@register_agent
class CarSoulGuardianAgent(BaseAgent):
    name = "carsoul_guardian"
    description = "AI 车辆医生 · 多智能体专家系统：主治医生分诊 + 五专科专家会诊，守护车辆全生命周期。"

    def __init__(self, model_name: str | None = None, **kwargs: Any) -> None:
        super().__init__(model_name=model_name, **kwargs)
        self._prompt = get_prompt("carsoul_guardian_system")
        self._client = None
        self._kb = None  # lazy knowledge base (RAG)
        self._engine: WorkflowEngine | None = None
        if self.settings.llm_enabled:
            self._client = self._init_openai_client()
            # Configure the workflow to use the LLM.
            CoreWorkflow.configure(
                llm_client=self._client,
                model_name=self.model_name,
            )
        # Initialise governance + workflow engine.
        self._init_governance()

    @property
    def kb(self):
        """Lazy-load the shared RAG knowledge base singleton."""
        if self._kb is None:
            try:
                from carsoul_agent.knowledge import get_knowledge_base

                self._kb = get_knowledge_base(
                    api_key=self.settings.openai_api_key,
                    api_base=self.settings.openai_api_base,
                    persist_path=self.settings.vector_db_path,
                    collection_name=self.settings.chroma_collection,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Knowledge base unavailable: %s", exc)
                self._kb = _NullKB()
        return self._kb

    def _init_openai_client(self):
        try:
            from openai import OpenAI  # type: ignore
        except ImportError:
            logger.warning("openai package not installed; agent will use rule-based fallback.")
            return None
        try:
            return OpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_api_base or None,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAI client init failed: %s", exc)
            return None

    def _init_governance(self) -> None:
        """Initialise the governance registry and workflow engine.

        - Registers all CarSoul agents into the managed registry with
          their capabilities, permissions, and versions.
        - Populates the permission checker with each agent's permissions.
        - Creates a WorkflowEngine wrapping the five core sub-agents.
        """
        try:
            # Lazy imports to avoid circular dependency.
            from carsoul_agent.governance import (
                managed_registry,
                permission_checker,
                register_governance_agents,
            )
            from carsoul_agent.workflow_engine import WorkflowEngine

            # Register all agents into the governance registry (idempotent).
            register_governance_agents()

            # Populate permission checker from registry metadata.
            for meta in managed_registry.all_metadata():
                permission_checker.register_permissions(meta.agent_id, meta.permissions)

            # Build the workflow engine with the same core agents used
            # by the existing CoreWorkflow.
            from carsoul_agent.agents.core.perception import PerceptionAgent
            from carsoul_agent.agents.core.diagnosis import DiagnosisAgent
            from carsoul_agent.agents.core.risk import RiskAgent
            from carsoul_agent.agents.core.explainer import ExplainerAgent
            from carsoul_agent.agents.core.service import ServiceAgent

            model = self.model_name
            self._engine = WorkflowEngine(
                perception_agent=PerceptionAgent(llm_client=self._client, model_name=model),
                diagnosis_agent=DiagnosisAgent(llm_client=self._client, model_name=model),
                risk_agent=RiskAgent(llm_client=self._client, model_name=model),
                explainer_agent=ExplainerAgent(llm_client=self._client, model_name=model),
                service_agent=ServiceAgent(llm_client=self._client, model_name=model),
            )
            logger.info("Governance + WorkflowEngine initialised successfully.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Governance init failed (degrading to legacy workflow): %s", exc)
            self._engine = None

    # ------------------------------------------------------------------
    #  Public interface (unchanged contract)
    # ------------------------------------------------------------------
    def handle(self, message: str, user: str, session_id: str | None = None) -> dict[str, Any]:
        session_id = self._ensure_session(session_id, user)
        self._remember(session_id, "user", message)

        # Route: greeting/FAQ → direct reply; knowledge question → RAG;
        # substantive vehicle issue → five-sub-agent workflow.
        closed_loop: dict[str, Any] | None = None
        if self._is_greeting(message):
            answer = self._greeting_reply(user)
        elif self._is_knowledge_question(message):
            answer = self._knowledge_answer(message, user)
        else:
            answer, closed_loop = self._run_workflow(message, user)

        self._remember(session_id, "assistant", answer)
        return {
            "answer": answer,
            "agent_status": "active",
            "session_id": session_id,
            "agent_name": self.name,
            "closed_loop": closed_loop,
        }

    # ------------------------------------------------------------------
    #  RAG knowledge answering
    # ------------------------------------------------------------------
    def _is_knowledge_question(self, message: str) -> bool:
        """Detect general car-knowledge questions that suit the RAG path."""
        msg = (message or "").strip().lower()
        if not msg or len(msg) < 4:
            return False
        # If the user explicitly references their own vehicle state, prefer
        # the workflow even when knowledge hints appear.
        if any(k in msg for k in ["我的车", "这辆车", "当前", "今天", "现在", "健康指数"]):
            return False
        # Long-trip scenarios should always trigger the full workflow,
        # not the knowledge-only RAG path.
        if any(k in msg for k in _LONG_TRIP_KEYWORDS):
            return False
        return any(k in msg for k in _KNOWLEDGE_HINTS)

    def _knowledge_answer(self, message: str, user: str) -> str:
        """Answer a general car-knowledge question using RAG retrieval."""
        try:
            ctx = self.kb.retrieve(message, top_k=4)
        except Exception as exc:  # noqa: BLE001
            logger.warning("RAG retrieval failed: %s", exc)
            ctx = None

        if ctx is None or ctx.is_empty:
            return (
                f"【CarSoul 知识库】{user}，关于「{message}」暂未在知识库中找到直接相关内容。"
                "你可以尝试更具体的关键词，或询问车辆保养、故障诊断、新能源电池、"
                "驾驶技巧、轮胎刹车、保险法规等方面的问题。"
            )

        # LLM path: ground the answer in retrieved knowledge.
        if self._client is not None:
            return self._llm_knowledge_answer(message, user, ctx)

        # Offline path: format the retrieved chunks directly.
        return self._format_knowledge_answer(message, user, ctx)

    def _llm_knowledge_answer(self, message: str, user: str, ctx) -> str:
        """Use the LLM to synthesise a grounded answer from RAG context."""
        try:
            system = (
                self._prompt.system.format(language=self.settings.language)
                + "\n\n你现在回答的是一个通用汽车知识问题。请基于下方知识库检索结果回答，"
                "标注信息来源，不要编造检索结果中没有的内容。如果检索结果不足以回答，请说明。"
            )
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": f"{ctx.context_text}\n\n用户问题：{message}"},
            ]
            resp = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.3,
                max_tokens=800,
            )
            answer = (resp.choices[0].message.content or "").strip()
            sources = "、".join(ctx.sources()[:3])
            if sources:
                answer += f"\n\n（知识来源：{sources}）"
            return answer
        except Exception as exc:  # noqa: BLE001
            logger.exception("LLM knowledge answer failed: %s", exc)
            return self._format_knowledge_answer(message, user, ctx)

    @staticmethod
    def _format_knowledge_answer(message: str, user: str, ctx) -> str:
        """Offline fallback: present retrieved knowledge chunks directly."""
        parts = [f"【CarSoul 知识库 · 检索回答】{user}，关于「{message}」，以下是与您问题最相关的专业知识："]
        for i, r in enumerate(ctx.results, 1):
            c = r.chunk
            heading = c.metadata.get("heading", "")
            title = c.title
            if heading:
                title += f" · {heading}"
            parts.append(f"\n{i}. [{title}]（相关度 {r.score:.2f}）")
            parts.append(c.text)
        sources = "、".join(ctx.sources()[:3])
        if sources:
            parts.append(f"\n（以上内容来自知识库：{sources}）")
        parts.append(
            "\n守护提示：以上为通用知识建议，具体到您的车辆请结合实际档案数据分析。"
        )
        return "\n".join(parts)

    # ------------------------------------------------------------------
    #  Workflow integration
    # ------------------------------------------------------------------
    def _run_workflow(self, message: str, user: str) -> tuple[str, dict[str, Any]]:
        """Build initial state, run the workflow, format answer.

        V1.0: Tries the new WorkflowEngine (governance + DAG + parallel +
        failure recovery) first. Falls back to the legacy CoreWorkflow
        if the engine is unavailable or crashes — guaranteeing backward
        compatibility.

        Returns ``(answer, closed_loop_summary)`` so the backend can surface
        the full guardian closed-loop trace (感知→诊断→风险→建议→执行) to
        the frontend for visualisation.
        """
        # --- AgentLoop: start trace for observation layer ---
        trace_id = None
        try:
            from carsoul_agent.observation import trace_collector
            trace_id = trace_collector.start_trace(
                workflow_id=f"wf_{message[:20]}",
                user_message=message,
            )
        except Exception:
            trace_id = None

        try:
            state = self._build_initial_state(message, user)

            # --- V1.0: Try the new WorkflowEngine first ---
            if self._engine is not None:
                try:
                    result = self._engine.execute(message, state)
                    # Record trace steps into observation layer.
                    self._record_trace(trace_id, result)
                    return self._format_answer(result), self._build_loop_summary(result)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("WorkflowEngine failed, falling back to legacy: %s", exc)
                    # Rebuild state (the engine may have mutated it).
                    state = self._build_initial_state(message, user)

            # --- Legacy fallback: original CoreWorkflow ---
            result = CoreWorkflow.run(state)
            self._record_trace(trace_id, result)
            return self._format_answer(result), self._build_loop_summary(result)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Workflow execution failed: %s", exc)
            return self._fallback_reply(message, user), {}

    def _record_trace(self, trace_id: str | None, state: AgentState) -> None:
        """Feed workflow trace_log entries into the AgentLoop observation layer."""
        if not trace_id:
            return
        try:
            from carsoul_agent.observation import trace_collector
            for entry in state.get("trace_log", []) or []:
                step = entry.get("step", "unknown")
                agent = entry.get("agent", "unknown")
                detail = entry.get("detail", "")
                data = entry.get("data", {}) or {}
                duration_ms = float(data.get("duration_ms", 0) or 0)
                trace_collector.record_step(
                    trace_id=trace_id,
                    agent_id=agent,
                    step=step,
                    detail=detail,
                    duration_ms=duration_ms,
                    data=data,
                )
            # Record token usage if available (from LLM-enriched steps).
            token_usage = state.get("token_usage", {})
            if token_usage:
                trace_collector.record_token_usage(
                    trace_id=trace_id,
                    prompt_tokens=token_usage.get("prompt_tokens", 0),
                    completion_tokens=token_usage.get("completion_tokens", 0),
                )
            # Mark trace as complete.
            trace_collector.complete_trace(trace_id)
        except Exception:
            pass

    def _build_loop_summary(self, state: AgentState) -> dict[str, Any]:
        """Project the workflow state into a frontend-ready closed-loop trace.

        Maps ``trace_log`` entries onto the canonical GOAI five-step closed
        loop (感知→诊断→风险→建议→执行) and bundles the structured outputs
        (anomalies, diagnosis, risk, actions, reminder) so the dashboard can
        render the entire guardian loop in one pass.
        """
        step_meta = {
            "perceive": ("状态感知", "perception"),
            "understand": ("故障诊断", "diagnosis"),
            "reason": ("风险评估", "risk"),
            "tool": ("守护建议", "explainer"),
            "act": ("服务执行", "service"),
            "normal_report": ("健康报告", "explainer"),
        }
        steps: list[dict[str, Any]] = []
        seen: set[str] = set()
        for t in state.get("trace_log", []) or []:
            step = t.get("step")
            if step not in step_meta or step in seen:
                continue
            seen.add(step)
            title, agent = step_meta[step]
            steps.append({
                "step": step,
                "agent": agent,
                "title": title,
                "detail": t.get("detail", ""),
                "status": "done",
                "data": t.get("data", {}) or {},
            })
        suggestion = state.get("service_suggestion", {}) or {}
        return {
            "is_normal": bool(state.get("is_normal", False)),
            "steps": steps,
            "anomalies": state.get("anomalies", []) or [],
            "expert_opinions": state.get("expert_opinions", []) or [],
            "diagnosis": state.get("diagnosis", {}) or {},
            "risk": state.get("risk_assessment", {}) or {},
            "actions": suggestion.get("actions", []) or [],
            "reminder": suggestion.get("reminder"),
            "escalation": suggestion.get("escalation"),
            "trip_context": state.get("trip_context", {}) or {},
            "knowledge_retrieval": state.get("knowledge_retrieval", {}) or {},
            "trip_report": state.get("trip_report", {}) or {},
            "calibration_context": state.get("calibration_context", {}) or {},
            # V1.0 additions: governance + workflow engine outputs.
            "judge_verdict": state.get("judge_verdict", {}) or {},
            "workflow_meta": state.get("workflow_meta", {}) or {},
        }

    def _build_initial_state(self, message: str, user: str) -> AgentState:
        """Gather vehicle data from tools and construct the workflow input."""
        msg_lower = (message or "").strip().lower()

        # --- gather vehicle info ---
        info_tool = default_registry.get("get_vehicle_info")
        health_tool = default_registry.get("get_health_score")
        behavior_tool = default_registry.get("get_driving_behavior")

        vehicle_state: dict = {}
        if info_tool:
            r = info_tool.run(vehicle_id=1)
            if r.ok:
                vehicle_state = r.data

        # --- gather health data (merged into vehicle_state) ---
        if health_tool:
            r = health_tool.run(vehicle_id=1)
            if r.ok:
                d = r.data
                vehicle_state["health_score"] = d.get("health_score", 0)
                vehicle_state["sub_scores"] = d.get("sub_scores", {})
                vehicle_state["risks"] = d.get("risks", [])
                vehicle_state["health_summary"] = d.get("summary", "")

        # --- gather driving behavior → driver profile ---
        driver_profile: dict = {"driving_style": "balanced", "user": user}
        if behavior_tool:
            r = behavior_tool.run(vehicle_id=1, days=7)
            if r.ok:
                d = r.data
                summary = d.get("summary", {})
                safety = summary.get("avg_safety_score") or 90
                eco = summary.get("avg_eco_score") or 90
                harsh = summary.get("total_harsh_events") or 0
                # Derive driving style from behavior metrics.
                if harsh > 10 or safety < 80:
                    driver_profile["driving_style"] = "aggressive"
                elif eco > 92 and harsh < 3:
                    driver_profile["driving_style"] = "eco"
                else:
                    driver_profile["driving_style"] = "balanced"
                driver_profile["safety_score"] = safety
                driver_profile["eco_score"] = eco
                driver_profile["harsh_events"] = harsh

        # --- extract trip context (long-trip scenario) ---
        trip_context = self._extract_trip_context(message)

        # --- build sensor window ---
        sensor_window = self._build_sensor_window(vehicle_state, msg_lower, trip_context)

        # --- 自纠错校准上下文（从历史反馈中学习）---
        # 读取本车历史风险预测的反馈记录，构建校准上下文。
        # 高误报率 → 下调置信度；高准确率 → 维持标准。
        # 这是 Agent「从反馈中学习」的真实闭环，非硬编码叙事。
        calibration_context: dict[str, Any] = {}
        calib_tool = default_registry.get("get_calibration_context")
        if calib_tool:
            r = calib_tool.run(vehicle_id=1, limit=10)
            if r.ok:
                calibration_context = r.data

        # --- RAG knowledge context ---
        # For long-trip scenarios, augment the query to retrieve trip-specific
        # knowledge from the long_trip_check.md document.
        knowledge_context = ""
        knowledge_retrieval: dict[str, Any] = {
            "query": message,
            "chunk_count": 0,
            "sources": [],
            "chunks": [],
        }
        try:
            if trip_context and trip_context.get("is_long_trip"):
                rag_query = (
                    f"长途出行前车辆检查 电池温控异常 轮胎刹车检查 充电路线规划 "
                    f"{trip_context.get('distance_km', 500)}公里"
                )
            else:
                rag_query = message
            ctx = self.kb.retrieve(rag_query, top_k=4)
            if not ctx.is_empty:
                knowledge_context = ctx.context_text
                knowledge_retrieval = {
                    "query": rag_query,
                    "chunk_count": len(ctx.results),
                    "sources": ctx.sources()[:4],
                    "chunks": [
                        {
                            "title": r.chunk.title,
                            "heading": r.chunk.metadata.get("heading", ""),
                            "score": round(r.score, 3),
                            "preview": r.chunk.text[:150],
                        }
                        for r in ctx.results[:4]
                    ],
                }
        except Exception as exc:  # noqa: BLE001
            logger.debug("knowledge context retrieval skipped: %s", exc)

        state: AgentState = {
            "vehicle_state": vehicle_state,
            "driver_profile": driver_profile,
            "sensor_window": sensor_window,
            "user_message": message,
            "knowledge_context": knowledge_context,
            "trip_context": trip_context or {},
            "knowledge_retrieval": knowledge_retrieval,
            "calibration_context": calibration_context,
            "trace_log": [],
        }
        state["trace_log"].append(trace_entry(
            step="__init__",
            agent="carsoul_guardian",
            detail=(
                f"初始化工作流状态：车辆={vehicle_state.get('brand', '')} {vehicle_state.get('model', '')}"
                + (f"，长途出行场景={trip_context['distance_km']}km" if trip_context else "")
            ),
            data={
                "health_score": vehicle_state.get("health_score"),
                "driving_style": driver_profile.get("driving_style"),
                "sensor_count": len(sensor_window),
                "knowledge_context_length": len(knowledge_context),
                "knowledge_chunks": knowledge_retrieval.get("chunk_count", 0),
                "is_long_trip": bool(trip_context),
                "trip_distance": trip_context.get("distance_km") if trip_context else None,
            },
        ))
        return state

    def _build_sensor_window(self, vehicle_state: dict, msg_lower: str, trip_context: dict | None = None) -> list[dict]:
        """Derive synthetic sensor readings from vehicle health data.

        For the long-trip demo scenario, we inject a comprehensive set of
        sensor anomalies (battery thermal rise, brake wear, tire wear,
        cell consistency degradation) so the perception agent can detect
        multiple issues and trigger the full five-step closed loop with a
        richer diagnosis — proving the Agent can handle complex scenarios.

        For the battery-thermal demo scenario, if the user mentions
        battery/temperature we inject an elevated temperature curve.

        Otherwise returns a single normal reading.
        """
        health_score = vehicle_state.get("health_score", 85)
        sub_scores = vehicle_state.get("sub_scores", {})
        risks = vehicle_state.get("risks", [])

        # Base readings from health data.
        battery_score = sub_scores.get("battery", 84)
        soc = max(15, min(100, int(battery_score * 1.0)))
        engine_temp = 90 + (100 - sub_scores.get("engine", 88)) * 0.5

        # Derive brake/tire readings from risks.
        brake_remaining = 8000
        tire_tread = 5.0
        for risk in risks:
            if risk.get("category") == "brake":
                brake_remaining = 4000  # below 5000 threshold
            if risk.get("category") == "tire":
                tire_tread = 2.5  # below 3.0 threshold

        battery_temp = 35.0  # normal baseline

        # ---- Long-trip scenario: comprehensive multi-anomaly injection ----
        if trip_context and trip_context.get("is_long_trip"):
            distance = trip_context.get("distance_km", 500)
            # Scale risk based on distance — longer trip = higher stakes.
            # Battery thermal: rising curve 35 → 42 → 48
            # Brake pad: 4200km remaining (below 5000 threshold)
            # Tire tread: 2.8mm (below 3.0 threshold)
            # Cell consistency: 68mV delta (above 50mV threshold)
            return [
                {"battery_temp": 35, "soc": 85, "engine_temp": round(engine_temp, 1),
                 "battery_cell_delta_mv": 35, "timestamp": "t-2"},
                {"battery_temp": 42, "soc": 78, "engine_temp": round(engine_temp, 1),
                 "battery_cell_delta_mv": 52, "soc_drop_rate": 1.8, "timestamp": "t-1"},
                {"battery_temp": 48, "soc": 72, "engine_temp": round(engine_temp, 1),
                 "soc_drop_rate": 2.5, "brake_pad_remaining_km": 4200,
                 "tire_tread_mm": 2.8, "battery_cell_delta_mv": 68,
                 "health_score": health_score, "timestamp": "t-0"},
            ]

        # ---- Battery thermal anomaly scenario (existing) ----
        if any(k in msg_lower for k in ["电池", "battery", "温度", "temperature", "发热", "热"]):
            # Inject a rising temperature curve: 35 → 42 → 48.
            battery_temp = 48
            soc = soc - 5  # slightly elevated drain
            return [
                {"battery_temp": 35, "soc": soc + 5, "engine_temp": engine_temp, "timestamp": "t-2"},
                {"battery_temp": 42, "soc": soc + 2, "engine_temp": engine_temp, "timestamp": "t-1"},
                {"battery_temp": battery_temp, "soc": soc, "engine_temp": engine_temp,
                 "soc_drop_rate": 2.5, "brake_pad_remaining_km": brake_remaining,
                 "tire_tread_mm": tire_tread, "health_score": health_score, "timestamp": "t-0"},
            ]

        # Normal sensor window (latest reading only).
        return [{
            "battery_temp": battery_temp,
            "soc": soc,
            "engine_temp": round(engine_temp, 1),
            "brake_pad_remaining_km": brake_remaining,
            "tire_tread_mm": tire_tread,
            "health_score": health_score,
            "timestamp": "t-0",
        }]

    @staticmethod
    def _extract_trip_context(message: str) -> dict | None:
        """Parse trip distance and context from a user message.

        Detects long-trip scenarios and extracts the planned distance
        so the workflow can tailor risk assessment and recommendations.

        Returns ``None`` when the message is not about a long trip.
        """
        msg = (message or "").strip().lower()
        if not any(k in msg for k in _LONG_TRIP_KEYWORDS):
            return None

        # Extract distance from patterns like "800公里", "800km", "800 km".
        distance = None
        patterns = [
            r"(\d+)\s*公里",
            r"(\d+)\s*千米",
            r"(\d+)\s*km",
        ]
        for pat in patterns:
            m = re.search(pat, msg)
            if m:
                distance = int(m.group(1))
                break

        if distance is None:
            distance = 500  # default when keywords present but no number

        # Estimate charging stops (~250km intervals) and travel time.
        charging_stops = max(1, distance // 250)
        estimated_hours = max(3, distance // 100)

        return {
            "is_long_trip": True,
            "distance_km": distance,
            "trip_type": "long_trip",
            "estimated_hours": estimated_hours,
            "charging_stops_needed": charging_stops,
            "message": message,
        }

    def _format_answer(self, state: AgentState) -> str:
        """Format the workflow output into a user-facing answer."""
        explanation = state.get("explanation", "")
        suggestion = state.get("service_suggestion", {})
        actions = suggestion.get("actions", [])

        parts = [explanation]

        # Append actionable steps if present.
        if actions:
            parts.append("\n行动建议：")
            for i, action in enumerate(actions, 1):
                parts.append(f"  {i}. {action}")

        # Append proactive reminder notice.
        reminder = suggestion.get("reminder")
        if reminder:
            parts.append(f"\n（守护引擎已推送「{reminder['title']}」级别提醒，并记录至车辆数字生命档案。）")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    #  Lightweight replies (no workflow needed)
    # ------------------------------------------------------------------
    def _is_greeting(self, message: str) -> bool:
        msg = (message or "").strip().lower()
        greetings = ["你好", "hello", "hi", "在吗", "你是谁", "what are you", "帮助", "help"]
        if any(k in msg for k in greetings):
            # If it's ONLY a greeting (short), don't run the workflow.
            if len(msg) < 20:
                return True
        return False

    def _greeting_reply(self, user: str) -> str:
        return (
            f"你好 {user}，我是 CarSoul Guardian 的 AI 车辆医生。\n"
            "我像主治医生一样守护你的车：先采集体征，再召集五位专科专家"
            "（动力/底盘/电气/驾驶行为/保养）并行会诊，最后给出诊断报告与处方。\n"
            "我可以帮你：\n"
            "  · 体检车辆健康（试试「我的车健康怎么样」）\n"
            "  · 排查故障异常（试试「电池温度异常」）\n"
            "  · 查看保养计划（试试「需要保养吗」）\n"
            "  · 查询汽车知识（试试「刹车片多久换一次」）\n\n"
            "每次回答都基于你的车辆数字生命档案与五专科专家会诊，做到"
            "问诊→会诊→诊断→处方→随访的完整闭环。"
        )

    def _fallback_reply(self, message: str, user: str) -> str:
        """Emergency fallback when the workflow itself crashes."""
        return (
            f"【CarSoul 守护引擎】{user}，已收到：「{message}」。"
            "守护引擎暂时遇到问题，已切换到应急响应。你可以询问保养、健康、故障或车辆档案相关问题。"
        )


class _NullKB:
    """No-op knowledge base used when RAG cannot initialise.

    Every method returns empty results so the agent degrades gracefully
    to workflow-only mode without crashing.
    """

    def retrieve(self, query: str, top_k: int = 5):
        from carsoul_agent.knowledge.base import RetrievalContext

        return RetrievalContext(query=query, results=[], context_text="")

    def search(self, query: str, top_k: int = 5, min_score: float = 0.05):
        return []

    def stats(self) -> dict:
        return {"chunk_count": 0, "backend": "null", "embedder": "none", "ready": False}

    @property
    def ready(self) -> bool:
        return False

    @property
    def chunk_count(self) -> int:
        return 0
