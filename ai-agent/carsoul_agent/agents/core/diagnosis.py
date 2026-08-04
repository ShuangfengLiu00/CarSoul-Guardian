"""Sub-agent ②: 故障诊断 (diagnosis) — AI 车辆医生会诊中枢.

This node is the **consultation hub** of the AI Vehicle Doctor. It runs
the multi-agent expert panel (专家会诊): five specialists each render a
domain opinion, then this agent synthesises them into a unified
diagnosis — the medical-style "会诊结论".

Pipeline:
  1. Run the expert panel → ``expert_opinions[]`` (parallel specialists).
  2. Collect all findings across experts; pick the most severe as the
     primary diagnosis, keep the rest as secondary.
  3. Any anomaly no expert claimed gets a generic fallback diagnosis.
  4. Optional LLM enrichment refines the primary root cause.

Output: ``diagnosis`` dict with ``primary``, ``secondary``, ``total``,
plus ``expert_opinions`` mirrored into state for the closed-loop trace.
"""
from __future__ import annotations

import logging
from typing import Any

from carsoul_agent.agents.core.experts import build_expert_panel, run_expert_panel
from carsoul_agent.agents.core.extended_experts import build_full_expert_panel
from carsoul_agent.agents.core.state import AgentState, Trace, trace_entry

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {"info": 1, "low": 2, "medium": 3, "high": 4, "urgent": 5}


class DiagnosisAgent:
    """Node ② — 故障诊断 Agent (专家会诊汇总)."""

    name = "diagnosis"
    description = "召集十专科专家并行会诊，汇总各专家意见，输出统一诊断结论。"

    def __init__(self, llm_client: Any | None = None, model_name: str = "gpt-4o-mini") -> None:
        self._llm = llm_client
        self._model = model_name
        # Build the full expert panel (10 specialists); reuse across runs.
        self._experts = build_full_expert_panel(llm_client=llm_client, model_name=model_name)

    # ------------------------------------------------------------------
    def run(self, state: AgentState) -> AgentState:
        anomalies: list[dict] = state.get("anomalies", [])
        trace: list[dict] = state.get("trace_log", [])

        # --- Stage 1: expert panel consultation -----------------------
        opinions = run_expert_panel(state, experts=self._experts)
        state["expert_opinions"] = opinions

        consulted = sum(1 for o in opinions if o.get("consulted"))
        total_findings = sum(o.get("finding_count", 0) for o in opinions)

        trace.append(trace_entry(
            step=Trace.UNDERSTAND,
            agent=self.name,
            detail=(
                f"专家会诊完成：{consulted}/{len(opinions)} 位专家参与，"
                f"共 {total_findings} 条发现"
            ),
            data={
                "experts": [o.get("specialty") for o in opinions],
                "consulted": consulted,
                "total_findings": total_findings,
            },
        ))

        # --- Stage 2: synthesise findings into diagnoses --------------
        diagnoses: list[dict] = self._synthesise(opinions, anomalies)

        # Fallback: anomalies no expert claimed.
        claimed_items = set()
        for d in diagnoses:
            ev = d.get("evidence", {})
            anomaly = ev.get("anomaly") or {}
            item = anomaly.get("item")
            if item:
                claimed_items.add(item)
        for anomaly in anomalies:
            if anomaly.get("item") not in claimed_items and anomaly.get("category") not in (
                claimed_items
            ):
                diagnoses.append({
                    "type": "unknown",
                    "root_cause": f"{anomaly.get('item', '未知项')}异常",
                    "severity": anomaly.get("level", "info"),
                    "description": anomaly.get("detail", "检测到异常，需进一步诊断。"),
                    "actions_hint": ["联系专业检修进一步排查"],
                    "recommendation": "联系专业检修进一步排查。",
                    "evidence": {"anomaly": anomaly},
                    "confidence": 0.5,
                    "source": "fallback",
                    "specialty": "通用",
                })

        # --- Stage 3: LLM enrichment (optional) -----------------------
        if self._llm is not None and diagnoses:
            self._llm_enrich(diagnoses, state)
        else:
            # Offline mode: rule-based knowledge matching.
            self._rule_based_knowledge_match(
                diagnoses, state.get("knowledge_context", "")
            )

        # Pick the most severe as primary; keep rest as secondary.
        diagnoses.sort(
            key=lambda d: _SEVERITY_ORDER.get(d.get("severity", "info"), 0),
            reverse=True,
        )
        primary = diagnoses[0] if diagnoses else {}
        secondary = diagnoses[1:] if len(diagnoses) > 1 else []

        diagnosis_out = {
            "primary": primary,
            "secondary": secondary,
            "total": len(diagnoses),
            "expert_opinions": opinions,
        }

        trace.append(trace_entry(
            step=Trace.REASON,
            agent=self.name,
            detail=(
                f"会诊结论：{primary.get('root_cause', '无异常')}"
                f"（来源 {primary.get('specialty', primary.get('source', 'N/A'))}，"
                f"置信度 {primary.get('confidence', 0)}）"
            ),
            data={
                "primary_type": primary.get("type"),
                "severity": primary.get("severity"),
                "confidence": primary.get("confidence"),
                "total_diagnoses": len(diagnoses),
                "expert_count": len(opinions),
            },
        ))

        state["diagnosis"] = diagnosis_out
        state["trace_log"] = trace
        return state

    # ------------------------------------------------------------------
    def _synthesise(self, opinions: list[dict], anomalies: list[dict]) -> list[dict]:
        """Flatten expert findings into a unified diagnosis list."""
        diagnoses: list[dict] = []
        for opinion in opinions:
            for finding in opinion.get("findings", []):
                diagnoses.append({
                    "type": finding.get("type", "unknown"),
                    "root_cause": finding.get("root_cause", "未知异常"),
                    "severity": finding.get("severity", "info"),
                    "description": finding.get("description", ""),
                    "actions_hint": [],
                    "recommendation": finding.get("recommendation", ""),
                    "evidence": finding.get("evidence", {}),
                    "confidence": finding.get("confidence", 0.7),
                    "source": finding.get("source", "expert"),
                    "specialty": opinion.get("specialty", "专科"),
                    "expert": opinion.get("expert", "expert"),
                })
        return diagnoses

    # ------------------------------------------------------------------
    def _llm_enrich(self, diagnoses: list[dict], state: AgentState) -> None:
        """Use LLM to refine the primary root cause and confidence.

        Injects ``knowledge_context`` (RAG retrieval results) into the
        prompt so the LLM can ground its reasoning in known failure cases.
        """
        try:
            import json
            vehicle = state.get("vehicle_state", {})
            knowledge_context = state.get("knowledge_context", "")

            # Build knowledge-enhanced prompt section.
            knowledge_section = ""
            if knowledge_context:
                knowledge_section = (
                    f"\n\n【知识库检索结果】\n{knowledge_context}\n"
                    "请结合以上知识库案例和故障模式，给出更精确的根因分析。"
                )

            prompt = (
                "你是 AI 车辆医生的主治诊断引擎。基于五专科专家的会诊发现，"
                "给出更精确的统一根因分析与置信度评估。\n"
                "输出 JSON：{\"root_cause\": str, \"confidence\": float, "
                "\"reasoning\": str, \"knowledge_match\": str}\n\n"
                f"车辆：{vehicle.get('brand', '')} {vehicle.get('model', '')} "
                f"{vehicle.get('year', '')}，里程 {vehicle.get('mileage', 'N/A')} km\n"
                f"首要诊断：{json.dumps(diagnoses[0], ensure_ascii=False, default=str)}"
                f"{knowledge_section}"
            )
            resp = self._llm.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=400,
            )
            text = (resp.choices[0].message.content or "").strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
            enrichment = json.loads(text)
            if enrichment.get("root_cause"):
                diagnoses[0]["root_cause"] = enrichment["root_cause"]
            if enrichment.get("confidence"):
                diagnoses[0]["confidence"] = enrichment["confidence"]
            if enrichment.get("knowledge_match"):
                diagnoses[0]["knowledge_match"] = enrichment["knowledge_match"]
            diagnoses[0]["source"] = "llm_enriched_with_rag"
        except Exception as exc:  # noqa: BLE001
            logger.debug("LLM diagnosis enrichment skipped: %s", exc)

    def _rule_based_knowledge_match(
        self, diagnoses: list[dict], knowledge_context: str
    ) -> None:
        """Offline mode: extract matching info from RAG knowledge context.

        When no LLM is available, we do simple keyword matching against
        the retrieved knowledge base text so the diagnosis still carries
        a ``knowledge_match`` annotation.
        """
        if not knowledge_context:
            return
        for d in diagnoses:
            root_cause = d.get("root_cause", "")
            description = d.get("description", "")
            # Check if the root cause or description keywords appear in
            # the knowledge context.
            search_text = root_cause
            if not search_text:
                continue
            # Try a few keyword extractions strategies.
            keywords = [search_text]
            # Also try shorter substrings (first 4+ chars).
            if len(search_text) > 4:
                keywords.append(search_text[:4])

            matched = False
            for kw in keywords:
                if kw in knowledge_context:
                    d["knowledge_match"] = (
                        f"知识库中找到相关案例：{kw}"
                    )
                    d["source"] = "rule_kb_matched"
                    matched = True
                    break

            if not matched and description:
                # Try matching on description keywords.
                desc_keywords = description[:6]
                if len(desc_keywords) >= 4 and desc_keywords in knowledge_context:
                    d["knowledge_match"] = (
                        f"知识库中找到相关描述：{desc_keywords}"
                    )
                    d["source"] = "rule_kb_matched"
