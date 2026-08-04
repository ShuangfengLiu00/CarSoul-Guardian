"""Multi-agent expert panel for the AI Vehicle Doctor.

This module realises the **多智能体车辆专家系统** layer: five specialist
agents that run in parallel and each render a domain opinion on the
anomalies detected by the perception node. The DiagnosisAgent then
synthesises their opinions into a unified diagnosis — a medical-style
"expert consultation" (专家会诊).

Each expert:
  - Owns a set of anomaly ``categories`` (its specialty).
  - Carries a domain knowledge base of failure modes.
  - Optionally inspects ``vehicle_state`` / ``driver_profile`` for
    domain signals the rule engine may have missed.
  - Returns an ``ExpertOpinion`` dict (findings, severity, recommendation,
    confidence) that the synthesiser merges.

The experts are intentionally pure-Python and offline-capable. When an
LLM client is configured, each expert can enrich its opinion with
natural-language reasoning; otherwise rule-based mode is used.

Experts (专科):
  1. PowertrainExpert   — 动力系统 (电池 / 发动机 / 电机)
  2. ChassisExpert      — 底盘系统 (刹车 / 轮胎 / 悬挂)
  3. ElectricalExpert   — 电气系统 (传感器 / 电路 / 电子)
  4. DrivingBehaviorExpert — 驾驶行为 (习惯 / 安全评分)
  5. MaintenanceExpert  — 保养规划 (周期 / 成本 / 优先级)
"""
from __future__ import annotations

import logging
from typing import Any

from carsoul_agent.agents.core.state import AgentState

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {"info": 1, "low": 2, "medium": 3, "high": 4, "urgent": 5}
# Normalise anomaly "level" → expert severity scale.
_LEVEL_TO_SEV = {
    "info": "info",
    "low": "low",
    "warning": "medium",
    "urgent": "high",
    "critical": "urgent",
}


def _max_severity(severities: list[str]) -> str:
    if not severities:
        return "info"
    return max(severities, key=lambda s: _SEVERITY_ORDER.get(s, 0))


def _severity_from_anomaly(level: str) -> str:
    return _LEVEL_TO_SEV.get(level, "info")


# ------------------------------------------------------------------ #
#  Base specialist
# ------------------------------------------------------------------ #
class ExpertAgent:
    """Base class for a specialist in the expert panel."""

    name: str = "expert"
    specialty: str = "专科"
    categories: tuple[str, ...] = ()
    description: str = ""

    def __init__(self, llm_client: Any | None = None, model_name: str = "gpt-4o-mini") -> None:
        self._llm = llm_client
        self._model = model_name

    # Public contract ------------------------------------------------
    def consult(self, state: AgentState) -> dict:
        """Render a domain opinion. Always returns a dict (never raises)."""
        anomalies: list[dict] = state.get("anomalies", [])
        relevant = [a for a in anomalies if a.get("category") in self.categories]

        findings = self._analyse(relevant, state)
        if self._llm is not None and findings:
            self._llm_enrich(findings, state)

        severities = [f.get("severity", "info") for f in findings]
        severity = _max_severity(severities)
        recommendation = self._recommendation(findings, state)

        return {
            "specialty": self.specialty,
            "expert": self.name,
            "findings": findings,
            "finding_count": len(findings),
            "severity": severity,
            "recommendation": recommendation,
            "confidence": self._confidence(findings),
            "consulted": True,
        }

    # Hooks for subclasses -------------------------------------------
    def _analyse(self, relevant: list[dict], state: AgentState) -> list[dict]:
        """Match anomalies against the expert's domain failure modes."""
        return []

    def _recommendation(self, findings: list[dict], state: AgentState) -> str:
        if not findings:
            return f"{self.specialty}未发现异常，维持常规关注。"
        top = max(findings, key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "info"), 0))
        return top.get("recommendation", f"关注{self.specialty}相关指标。")

    def _confidence(self, findings: list[dict]) -> float:
        if not findings:
            return 0.9
        return max(f.get("confidence", 0.7) for f in findings)

    def _llm_enrich(self, findings: list[dict], state: AgentState) -> None:
        """Optional LLM refinement of the top finding's reasoning.

        Injects ``knowledge_context`` (RAG retrieval results) into the
        prompt so the expert can ground its reasoning in known cases.
        """
        try:
            import json
            vehicle = state.get("vehicle_state", {})
            knowledge_context = state.get("knowledge_context", "")

            knowledge_section = ""
            if knowledge_context:
                knowledge_section = (
                    f"\n\n【相关知识库内容】\n{knowledge_context}\n"
                    "请结合以上知识判断根因是否与历史案例匹配。"
                )

            prompt = (
                f"你是{self.specialty}专家。基于以下发现，给出更精确的根因与置信度。\n"
                "输出 JSON：{\"root_cause\": str, \"confidence\": float, "
                "\"reasoning\": str, \"knowledge_match\": str}\n\n"
                f"车辆：{vehicle.get('brand', '')} {vehicle.get('model', '')}，"
                f"里程 {vehicle.get('mileage', 'N/A')} km\n"
                f"发现：{json.dumps(findings[0], ensure_ascii=False)}"
                f"{knowledge_section}"
            )
            resp = self._llm.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
            )
            text = (resp.choices[0].message.content or "").strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
            enrichment = json.loads(text)
            if enrichment.get("root_cause"):
                findings[0]["root_cause"] = enrichment["root_cause"]
            if enrichment.get("confidence"):
                findings[0]["confidence"] = enrichment["confidence"]
            if enrichment.get("knowledge_match"):
                findings[0]["knowledge_match"] = enrichment["knowledge_match"]
            findings[0]["source"] = "llm_enriched_with_rag"
        except Exception as exc:  # noqa: BLE001
            logger.debug("%s LLM enrich skipped: %s", self.name, exc)

    # Helpers --------------------------------------------------------
    @staticmethod
    def _match_modes(relevant: list[dict], modes: list[dict]) -> list[dict]:
        """Match anomalies against a list of failure-mode patterns."""
        out: list[dict] = []
        for anomaly in relevant:
            for mode in modes:
                if _match(anomaly, mode.get("match", {})):
                    out.append({
                        "type": mode["type"],
                        "root_cause": mode["root_cause"],
                        "severity": mode["severity"],
                        "description": mode["description"],
                        "recommendation": "；".join(mode.get("actions_hint", [])),
                        "evidence": {"anomaly": anomaly, "matched_pattern": mode["match"]},
                        "confidence": 0.85,
                        "source": "rule_kb",
                    })
                    break
        return out


def _match(anomaly: dict, pattern_match: dict) -> bool:
    for k, v in pattern_match.items():
        if anomaly.get(k) != v:
            return False
    return True


# ------------------------------------------------------------------ #
#  1. 动力系统专家
# ------------------------------------------------------------------ #
_POWERTRAIN_MODES: list[dict] = [
    {
        "match": {"category": "battery", "item": "电池温度"},
        "type": "battery_thermal",
        "root_cause": "电芯热失控早期征兆",
        "severity": "high",
        "description": "电池温度持续升高，可能由散热系统异常或电芯内短路引起，存在热失控风险。",
        "actions_hint": ["立即靠边停车并关闭高功耗设备", "联系授权服务中心检测电池模组"],
    },
    {
        "match": {"category": "battery", "item": "电量下降速率"},
        "type": "battery_drain",
        "root_cause": "异常电量损耗",
        "severity": "medium",
        "description": "电量下降速率超出正常范围，可能存在暗电流或电池老化。",
        "actions_hint": ["检查未关闭用电设备", "预约电池健康检测"],
    },
    {
        "match": {"category": "battery", "item": "电量"},
        "type": "low_soc",
        "root_cause": "电量过低",
        "severity": "low",
        "description": "当前电量不足以支撑长距离行驶，建议尽快充电。",
        "actions_hint": ["规划就近充电站", "避免高速行驶以降低能耗"],
    },
    {
        "match": {"category": "engine", "item": "发动机温度"},
        "type": "engine_overheat",
        "root_cause": "发动机过热",
        "severity": "high",
        "description": "冷却系统可能异常，继续行驶可能导致发动机损伤。",
        "actions_hint": ["立即靠边停车", "等待冷却后检查冷却液"],
    },
]


class PowertrainExpert(ExpertAgent):
    """动力系统专家 — 电池 / 发动机 / 电机."""

    name = "powertrain_expert"
    specialty = "动力系统"
    categories = ("battery", "engine", "motor", "powertrain")
    description = "负责电池、发动机/电机等动力总成的健康与会诊。"

    def _analyse(self, relevant: list[dict], state: AgentState) -> list[dict]:
        findings = self._match_modes(relevant, _POWERTRAIN_MODES)

        # Domain signal: SOC health derived from sub-scores.
        vehicle = state.get("vehicle_state", {})
        sub_scores = vehicle.get("sub_scores", {})
        battery_score = sub_scores.get("battery")
        if battery_score is not None and battery_score < 70 and not any(
            f.get("type") == "low_soc" for f in findings
        ):
            findings.append({
                "type": "battery_aging",
                "root_cause": "电池健康度偏低",
                "severity": "medium",
                "description": f"电池子系统评分 {battery_score}/100，存在老化或衰减迹象。",
                "recommendation": "预约电池 SOH 检测，关注续航衰减趋势。",
                "evidence": {"sub_score": battery_score},
                "confidence": 0.7,
                "source": "domain_signal",
            })
        return findings


# ------------------------------------------------------------------ #
#  2. 底盘系统专家
# ------------------------------------------------------------------ #
_CHASSIS_MODES: list[dict] = [
    {
        "match": {"category": "brake", "item": "刹车片"},
        "type": "brake_pad_wear",
        "root_cause": "刹车片磨损到达极限",
        "severity": "medium",
        "description": "刹车片剩余里程不足，制动距离可能延长，影响行车安全。",
        "actions_hint": ["尽快更换刹车片", "避免急刹车驾驶"],
    },
    {
        "match": {"category": "tire", "item": "轮胎"},
        "type": "tire_wear",
        "root_cause": "轮胎胎纹接近磨损极限",
        "severity": "medium",
        "description": "轮胎抓地力下降，雨天制动距离显著增加。",
        "actions_hint": ["更换轮胎或前后对调", "雨天减速行驶"],
    },
]


class ChassisExpert(ExpertAgent):
    """底盘系统专家 — 刹车 / 轮胎 / 悬挂."""

    name = "chassis_expert"
    specialty = "底盘系统"
    categories = ("brake", "tire", "suspension", "chassis")
    description = "负责制动、轮胎、悬挂等底盘部件的磨损与安全会诊。"

    def _analyse(self, relevant: list[dict], state: AgentState) -> list[dict]:
        findings = self._match_modes(relevant, _CHASSIS_MODES)

        # Domain signal: derive chassis wear from mileage.
        vehicle = state.get("vehicle_state", {})
        mileage = vehicle.get("mileage")
        if isinstance(mileage, (int, float)) and mileage > 80000 and not findings:
            findings.append({
                "type": "chassis_aging",
                "root_cause": "高里程底盘件老化",
                "severity": "low",
                "description": f"里程 {int(mileage)} km，底盘件（刹车盘/减震/球头）进入老化期。",
                "recommendation": "安排底盘全面检查，重点关注刹车盘与减震器。",
                "evidence": {"mileage": mileage},
                "confidence": 0.65,
                "source": "domain_signal",
            })
        return findings


# ------------------------------------------------------------------ #
#  3. 电气系统专家
# ------------------------------------------------------------------ #
class ElectricalExpert(ExpertAgent):
    """电气系统专家 — 传感器 / 电路 / 电子."""

    name = "electrical_expert"
    specialty = "电气系统"
    categories = ("electrical", "sensor", "circuit", "electronic")
    description = "负责传感器、线束、电子控制单元的信号与故障会诊。"

    def _analyse(self, relevant: list[dict], state: AgentState) -> list[dict]:
        findings: list[dict] = []
        for anomaly in relevant:
            findings.append({
                "type": "electrical_fault",
                "root_cause": f"{anomaly.get('item', '电气元件')}异常",
                "severity": _severity_from_anomaly(anomaly.get("level", "info")),
                "description": anomaly.get("detail", "检测到电气系统异常。"),
                "recommendation": "使用 OBD 读取故障码，排查相关线束与传感器。",
                "evidence": {"anomaly": anomaly},
                "confidence": 0.6,
                "source": "rule_kb",
            })

        # Domain signal: anomalous sensor readings (temp spikes) may hint at
        # sensor/ECU issues rather than the mechanical root cause.
        sensor_window = state.get("sensor_window", [])
        if sensor_window:
            latest = sensor_window[-1] if sensor_window else {}
            bt = latest.get("battery_temp")
            et = latest.get("engine_temp")
            if (isinstance(bt, (int, float)) and bt > 45) or (
                isinstance(et, (int, float)) and et > 110
            ):
                findings.append({
                    "type": "sensor_signal_check",
                    "root_cause": "温度信号异常需排除传感器误报",
                    "severity": "low",
                    "description": "温度读数偏高，建议先排除温度传感器/线束接触不良导致的误报。",
                    "recommendation": "交叉验证多路温度传感器读数，必要时校准或更换。",
                    "evidence": {"battery_temp": bt, "engine_temp": et},
                    "confidence": 0.55,
                    "source": "domain_signal",
                })
        return findings


# ------------------------------------------------------------------ #
#  4. 驾驶行为专家
# ------------------------------------------------------------------ #
class DrivingBehaviorExpert(ExpertAgent):
    """驾驶行为专家 — 习惯 / 安全评分."""

    name = "driving_expert"
    specialty = "驾驶行为"
    categories = ("driving", "behavior", "safety")
    description = "结合驾驶者画像评估驾驶习惯对车辆健康与安全的影响。"

    def _analyse(self, relevant: list[dict], state: AgentState) -> list[dict]:
        findings: list[dict] = []
        profile = state.get("driver_profile", {})
        style = profile.get("driving_style", "balanced")
        harsh = profile.get("harsh_events")
        safety = profile.get("safety_score")

        if style == "aggressive":
            findings.append({
                "type": "aggressive_driving",
                "root_cause": "激烈驾驶风格加剧损耗",
                "severity": "medium",
                "description": "急加速/急刹车频次偏高，制动与轮胎负荷增大，安全风险上升。",
                "recommendation": "建议平稳驾驶，延长制动与轮胎寿命，降低安全风险。",
                "evidence": {"driving_style": style, "harsh_events": harsh},
                "confidence": 0.75,
                "source": "domain_signal",
            })
        elif style == "eco":
            findings.append({
                "type": "eco_driving_positive",
                "root_cause": "节能驾驶习惯良好",
                "severity": "info",
                "description": "驾驶风格节能，对能耗与部件寿命友好。",
                "recommendation": "保持当前驾驶习惯。",
                "evidence": {"driving_style": style},
                "confidence": 0.8,
                "source": "domain_signal",
            })

        if isinstance(safety, (int, float)) and safety < 80:
            findings.append({
                "type": "low_safety_score",
                "root_cause": "安全评分偏低",
                "severity": "medium",
                "description": f"近期安全评分 {safety}/100，存在风险驾驶行为。",
                "recommendation": "回顾近期急刹/急转事件，必要时参加安全驾驶提醒。",
                "evidence": {"safety_score": safety},
                "confidence": 0.7,
                "source": "domain_signal",
            })
        return findings


# ------------------------------------------------------------------ #
#  5. 保养规划专家
# ------------------------------------------------------------------ #
class MaintenanceExpert(ExpertAgent):
    """保养规划专家 — 周期 / 成本 / 优先级."""

    name = "maintenance_expert"
    specialty = "保养规划"
    categories = ("overall", "maintenance")
    description = "结合里程与综合健康，给出保养优先级与周期建议。"

    def _analyse(self, relevant: list[dict], state: AgentState) -> list[dict]:
        findings: list[dict] = []
        vehicle = state.get("vehicle_state", {})
        health_score = vehicle.get("health_score")
        mileage = vehicle.get("mileage")

        if isinstance(health_score, (int, float)) and health_score < 60:
            findings.append({
                "type": "general_health_decline",
                "root_cause": "综合健康指数偏低",
                "severity": "medium",
                "description": f"综合健康指数 {health_score}/100，多个子系统分数下降。",
                "recommendation": "安排全面检测，按优先级处理高风险项。",
                "evidence": {"health_score": health_score},
                "confidence": 0.7,
                "source": "domain_signal",
            })

        # Mileage-based maintenance cadence.
        if isinstance(mileage, (int, float)):
            next_interval = ((int(mileage) // 10000) + 1) * 10000
            km_to_service = next_interval - int(mileage)
            if km_to_service <= 1000:
                findings.append({
                    "type": "maintenance_due",
                    "root_cause": "保养周期临近",
                    "severity": "low",
                    "description": f"距下次保养里程约 {km_to_service} km（{next_interval} km 节点）。",
                    "recommendation": "预约常规保养（机油/机滤/检查项目）。",
                    "evidence": {"mileage": mileage, "next_interval": next_interval},
                    "confidence": 0.8,
                    "source": "domain_signal",
                })
        return findings


# ------------------------------------------------------------------ #
#  Panel orchestration
# ------------------------------------------------------------------ #
def build_expert_panel(
    llm_client: Any | None = None,
    model_name: str = "gpt-4o-mini",
) -> list[ExpertAgent]:
    """Instantiate the five specialist agents for a consultation."""
    return [
        PowertrainExpert(llm_client=llm_client, model_name=model_name),
        ChassisExpert(llm_client=llm_client, model_name=model_name),
        ElectricalExpert(llm_client=llm_client, model_name=model_name),
        DrivingBehaviorExpert(llm_client=llm_client, model_name=model_name),
        MaintenanceExpert(llm_client=llm_client, model_name=model_name),
    ]


def run_expert_panel(
    state: AgentState,
    experts: list[ExpertAgent] | None = None,
    parallel: bool = True,
) -> list[dict]:
    """Run all specialists and return their opinions.

    When ``parallel=True`` (default), the five specialists execute
    concurrently via a thread pool — realising the Parallel Workflow
    pattern (§6.2) from the Workflow Engine spec. Each expert reads
    the shared ``state`` (read-only) and returns an independent opinion.

    The order of opinions in the returned list is deterministic
    (powertrain → chassis → electrical → driving → maintenance) so the
    synthesiser can present a stable consultation record. Each expert
    is isolated: a failure in one does not abort the panel.
    """
    if experts is None:
        experts = build_expert_panel()

    if parallel and len(experts) > 1:
        return _run_expert_panel_parallel(experts, state)
    return _run_expert_panel_sequential(experts, state)


def _run_expert_panel_sequential(experts: list[ExpertAgent], state: AgentState) -> list[dict]:
    """Original sequential execution (fallback)."""
    opinions: list[dict] = []
    for expert in experts:
        try:
            opinions.append(expert.consult(state))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Expert %s failed: %s", expert.name, exc)
            opinions.append(_error_opinion(expert, exc))
    return opinions


def _run_expert_panel_parallel(experts: list[ExpertAgent], state: AgentState) -> list[dict]:
    """Parallel execution via ThreadPoolExecutor (§6.2 Parallel Workflow).

    Each expert runs in its own thread. Since experts only READ the
    shared ``state`` and return independent dicts, this is thread-safe
    under the GIL. Results are collected and re-ordered to match the
    original expert order for deterministic output.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=len(experts)) as pool:
        future_to_expert = {
            pool.submit(expert.consult, state): expert
            for expert in experts
        }
        for future in as_completed(future_to_expert):
            expert = future_to_expert[future]
            try:
                results[expert.name] = future.result()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Expert %s failed (parallel): %s", expert.name, exc)
                results[expert.name] = _error_opinion(expert, exc)

    # Re-order to match original expert sequence (deterministic output).
    return [results.get(e.name, _error_opinion(e, RuntimeError("missing"))) for e in experts]


def _error_opinion(expert: ExpertAgent, exc: Exception) -> dict:
    """Build an error opinion for a failed expert."""
    return {
        "specialty": expert.specialty,
        "expert": expert.name,
        "findings": [],
        "finding_count": 0,
        "severity": "info",
        "recommendation": f"{expert.specialty}会诊暂时不可用。",
        "confidence": 0.0,
        "consulted": False,
        "error": str(exc),
    }
