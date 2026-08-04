"""Judge Agent — 多Agent冲突治理 (§10).

When multiple expert agents disagree (e.g. Battery Agent says "battery
fault" while Driving Agent says "driving caused it"), the Judge Agent
arbitrates based on:

  1. 数据可信度 — how reliable is each agent's input data
  2. 历史准确率 — each agent's past success rate
  3. 模型评分 — the confidence score each agent reported

Output: a final fused conclusion with a confidence-weighted ranking.
"""
from __future__ import annotations

import logging
from typing import Any

from carsoul_agent.governance.registry import managed_registry

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {"info": 1, "low": 2, "medium": 3, "high": 4, "urgent": 5}


class JudgeAgent:
    """决策裁判Agent — resolves conflicts between expert opinions.

    Invoked by the workflow engine after the expert panel runs, when:
      - Two or more experts disagree on root cause
      - Severity levels conflict
      - The diagnosis needs a confidence-weighted final decision
    """

    name = "judge"
    description = "决策裁判Agent — 基于数据可信度、历史准确率、模型评分仲裁多Agent冲突。"

    def resolve(self, expert_opinions: list[dict]) -> dict[str, Any]:
        """Arbitrate among expert opinions and return a fused conclusion.

        Args:
            expert_opinions: List of expert opinion dicts (from experts.py).

        Returns:
            A dict with:
              - verdict: "consensus" | "conflict_resolved" | "insufficient_data"
              - primary_cause: the winning root cause
              - confidence: fused confidence [0..1]
              - contributor_weights: {expert_name: weight}
              - conflict_detected: bool
              - reasoning: human-readable explanation
        """
        if not expert_opinions:
            return self._insufficient("无专家意见可供仲裁。")

        # Filter to opinions that actually found something.
        substantive = [
            o for o in expert_opinions
            if o.get("finding_count", 0) > 0 and o.get("consulted")
        ]
        if not substantive:
            return self._insufficient("所有专家均未发现异常，无需仲裁。")

        # --- Detect conflict ---
        root_causes = set()
        severities = set()
        for o in substantive:
            for f in o.get("findings", []):
                root_causes.add(f.get("root_cause", ""))
                severities.add(f.get("severity", "info"))

        conflict_detected = len(root_causes) > 1 and len(substantive) > 1

        # --- Compute weights ---
        weights = {}
        for o in substantive:
            agent_id = o.get("expert", "")
            confidence = o.get("confidence", 0.5)
            # Historical accuracy from the registry.
            meta = managed_registry.get(agent_id)
            if meta and meta.total_invocations > 0:
                accuracy = meta.success_count / meta.total_invocations
            else:
                accuracy = 0.75  # default for new agents
            # Weight = 0.4 * confidence + 0.3 * accuracy + 0.3 * finding_count_factor
            finding_factor = min(1.0, o.get("finding_count", 1) / 3.0)
            weight = 0.4 * confidence + 0.3 * accuracy + 0.3 * finding_factor
            weights[agent_id] = round(weight, 3)

        # --- Select the winning opinion ---
        best_opinion = max(substantive, key=lambda o: weights.get(o.get("expert", ""), 0))
        best_expert = best_opinion.get("expert", "")
        best_finding = max(
            best_opinion.get("findings", [{}]),
            key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "info"), 0),
        )

        # --- Fuse confidence ---
        total_weight = sum(weights.values()) or 1.0
        fused_confidence = sum(
            weights.get(o.get("expert", ""), 0) * o.get("confidence", 0.5)
            for o in substantive
        ) / total_weight

        verdict = "conflict_resolved" if conflict_detected else "consensus"

        reasoning_parts = []
        if conflict_detected:
            reasoning_parts.append(
                f"检测到 {len(root_causes)} 种不同根因判断，触发冲突仲裁。"
            )
            reasoning_parts.append(
                f"基于置信度(40%)+历史准确率(30%)+发现数量(30%)加权后，"
                f"{best_expert} 的判断获最高权重 {weights[best_expert]}。"
            )
        else:
            reasoning_parts.append(
                f"专家意见一致，无需冲突仲裁。{best_expert} 的判断置信度最高。"
            )

        return {
            "verdict": verdict,
            "primary_cause": best_finding.get("root_cause", "未知"),
            "primary_type": best_finding.get("type", "unknown"),
            "primary_specialty": best_opinion.get("specialty", ""),
            "confidence": round(fused_confidence, 3),
            "contributor_weights": weights,
            "conflict_detected": conflict_detected,
            "root_causes_seen": sorted(root_causes),
            "severities_seen": sorted(severities, key=lambda s: _SEVERITY_ORDER.get(s, 0)),
            "reasoning": " ".join(reasoning_parts),
        }

    def _insufficient(self, reason: str) -> dict[str, Any]:
        return {
            "verdict": "insufficient_data",
            "primary_cause": None,
            "confidence": 0.0,
            "contributor_weights": {},
            "conflict_detected": False,
            "reasoning": reason,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.name,
            "name": "Judge Agent",
            "description": self.description,
        }
