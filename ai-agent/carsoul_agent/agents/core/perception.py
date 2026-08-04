"""Sub-agent ①: 状态感知 (perception).

Reads ``sensor_window`` + ``vehicle_state`` and detects anomalies via a
two-stage approach:

  1. Rule engine — hard thresholds (battery temp > 45 °C, SOC drop rate,
     brake-pad remaining km, tire-tread wear, etc.).
  2. Semantic layer — if an LLM is configured, a lightweight prompt asks
     the model to spot trends the rules might miss (e.g. SOC declining
     faster than expected). Offline mode skips this gracefully.

Output: ``anomalies[]`` + ``is_normal`` flag. When ``is_normal`` is True
the graph routes to the normal-report branch, skipping diagnosis/risk.
"""
from __future__ import annotations

import logging
from typing import Any

from carsoul_agent.agents.core.state import AgentState, Trace, trace_entry

logger = logging.getLogger(__name__)

# ---- threshold table (rule engine) -------------------------------- #
# Each rule: (metric_key, operator, threshold, anomaly_descriptor)
# The sensor_window items are dicts that may carry these metric keys.
THRESHOLDS: list[dict] = [
    {
        "metric": "battery_temp",
        "op": ">",
        "value": 45,
        "category": "battery",
        "item": "电池温度",
        "level": "warning",
        "detail": "电池温度 {actual}℃ 超过安全阈值 45℃",
    },
    {
        "metric": "battery_temp",
        "op": ">",
        "value": 48,
        "category": "battery",
        "item": "电池温度",
        "level": "urgent",
        "detail": "电池温度 {actual}℃ 接近热失控危险区",
    },
    {
        "metric": "soc",
        "op": "<",
        "value": 20,
        "category": "battery",
        "item": "电量",
        "level": "warning",
        "detail": "电量仅 {actual}%，建议尽快充电",
    },
    {
        "metric": "soc_drop_rate",
        "op": ">",
        "value": 2.0,
        "category": "battery",
        "item": "电量下降速率",
        "level": "warning",
        "detail": "电量下降速率 {actual}%/h，超出正常范围",
    },
    {
        "metric": "brake_pad_remaining_km",
        "op": "<",
        "value": 5000,
        "category": "brake",
        "item": "刹车片",
        "level": "warning",
        "detail": "刹车片剩余约 {actual} km，建议尽快更换",
    },
    {
        "metric": "tire_tread_mm",
        "op": "<",
        "value": 3.0,
        "category": "tire",
        "item": "轮胎",
        "level": "warning",
        "detail": "胎纹深度 {actual} mm，接近磨损极限",
    },
    {
        "metric": "engine_temp",
        "op": ">",
        "value": 110,
        "category": "engine",
        "item": "发动机温度",
        "level": "urgent",
        "detail": "发动机温度 {actual}℃，存在过热风险",
    },
    {
        "metric": "battery_cell_delta_mv",
        "op": ">",
        "value": 50,
        "category": "battery",
        "item": "电池一致性",
        "level": "warning",
        "detail": "电池模组电压差 {actual}mV 超过安全阈值 50mV，一致性下降",
    },
    {
        "metric": "health_score",
        "op": "<",
        "value": 60,
        "category": "overall",
        "item": "综合健康",
        "level": "warning",
        "detail": "综合健康指数 {actual}/100，需关注",
    },
]

# Also check vehicle_state risks (from the health tool).
_RISK_LEVEL_MAP = {"urgent": "urgent", "warning": "warning", "info": "info", "critical": "urgent"}


def _check_threshold(actual: float, op: str, threshold: float) -> bool:
    if op == ">":
        return actual > threshold
    if op == "<":
        return actual < threshold
    if op == ">=":
        return actual >= threshold
    if op == "<=":
        return actual <= threshold
    return False


class PerceptionAgent:
    """Node ① — 状态感知 Agent."""

    name = "perception"
    description = "读取传感器窗口与车辆快照，做阈值 + 语义异常检测，输出异常列表。"

    def __init__(self, llm_client: Any | None = None, model_name: str = "gpt-4o-mini") -> None:
        self._llm = llm_client
        self._model = model_name

    # ------------------------------------------------------------------
    def run(self, state: AgentState) -> AgentState:
        sensor_window: list[dict] = state.get("sensor_window", [])
        vehicle_state: dict = state.get("vehicle_state", {})
        trace: list[dict] = state.get("trace_log", [])

        anomalies: list[dict] = []

        # --- Stage 1: rule engine on the latest sensor reading --------
        latest = sensor_window[-1] if sensor_window else {}
        for rule in THRESHOLDS:
            metric = rule["metric"]
            if metric in latest:
                actual = latest[metric]
                if _check_threshold(actual, rule["op"], rule["value"]):
                    anomalies.append({
                        "category": rule["category"],
                        "item": rule["item"],
                        "level": rule["level"],
                        "metric": metric,
                        "actual": actual,
                        "threshold": rule["value"],
                        "detail": rule["detail"].format(actual=actual),
                    })

        # --- Stage 1b: check vehicle_state risks (health tool output) --
        for risk in vehicle_state.get("risks", []):
            level = _RISK_LEVEL_MAP.get(risk.get("level", "info"), "info")
            if level in ("warning", "urgent"):
                anomalies.append({
                    "category": risk.get("category", "overall"),
                    "item": risk.get("item", "未知"),
                    "level": level,
                    "detail": risk.get("detail", ""),
                    "recommendation": risk.get("recommendation"),
                    "source": "health_snapshot",
                })

        # --- Stage 2: semantic detection (LLM, optional) --------------
        if self._llm is not None and sensor_window:
            semantic = self._semantic_detect(sensor_window, vehicle_state)
            if semantic:
                anomalies.extend(semantic)

        is_normal = len(anomalies) == 0
        trace.append(trace_entry(
            step=Trace.PERCEIVE,
            agent=self.name,
            detail=f"检出 {len(anomalies)} 个异常" if anomalies else "未检出异常，走正常报告分支",
            data={"anomaly_count": len(anomalies), "is_normal": is_normal},
        ))

        state["anomalies"] = anomalies
        state["is_normal"] = is_normal
        state["trace_log"] = trace
        return state

    # ------------------------------------------------------------------
    def _semantic_detect(self, sensor_window: list[dict], vehicle_state: dict) -> list[dict]:
        """Ask the LLM to spot trend anomalies the rules might miss."""
        try:
            import json
            prompt = (
                "你是车辆状态感知引擎。分析以下传感器时序数据，找出规则引擎可能遗漏的趋势性异常。\n"
                "只输出 JSON 数组，每个元素包含 category/item/level/detail 字段。无异常则输出 []。\n\n"
                f"车辆：{vehicle_state.get('brand', '')} {vehicle_state.get('model', '')}\n"
                f"传感器读数：{json.dumps(sensor_window[-5:], ensure_ascii=False)}"
            )
            resp = self._llm.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=300,
            )
            text = (resp.choices[0].message.content or "").strip()
            # Tolerate markdown code fences.
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
            return json.loads(text) if text else []
        except Exception as exc:  # noqa: BLE001
            logger.debug("semantic detection skipped: %s", exc)
            return []
