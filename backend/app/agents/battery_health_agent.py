"""电池健康垂直 Agent（MVP 启用）。

调用 carModel 电池类工具：``predict_battery_health``（SOH/寿命/95% 预测区间）
+ ``explain_degradation``（多因子归因），输出健康分 + 置信区间 + 归因解读。

安全约束（任务硬性要求）：输出必须标注「趋势推演，非已发生故障，
需线下技师确认」。

P0 铁律：无 emoji / 无紫粉渐变 / 无 AI 模板味文案 / 无硬编码颜色。
"""
from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext, AgentResult
from app.agents.vertical_base import (
    VerticalAgentBase,
    soh_to_pct,
    worst_source,
)


class BatteryHealthAgent(VerticalAgentBase):
    name = "battery_health"
    domain = "battery"
    tools = ["predict_battery_health", "explain_degradation", "get_vehicle_state"]

    def parse(self, ctx: AgentContext) -> dict[str, Any]:
        return {"query": ctx.query}

    def execute(self, ctx: AgentContext, parsed: dict[str, Any]) -> AgentResult:
        vid = self.resolve_vehicle_id(ctx)
        if not vid:
            return self.no_vehicle_result()

        # 1) SOH / 寿命预测
        pred = self.call_tool(
            "predict_battery_health",
            {"vehicle_id": vid, "horizon_days": 90}, ctx)
        if pred.get("error"):
            return self.degrade_result(vid, pred, "电池健康度预测")

        pred_data = pred.get("data") or {}
        current = soh_to_pct(pred_data.get("current_soh"))
        predicted = soh_to_pct(pred_data.get("predicted_soh"))
        lo = soh_to_pct(pred_data.get("soh_pi95_low"))
        hi = soh_to_pct(pred_data.get("soh_pi95_high"))
        risk = pred_data.get("risk_level", "unknown")
        horizon = pred_data.get("horizon_days", 90)
        sigma = pred_data.get("sigma_soh")
        calibrated = pred_data.get("calibrated", False)

        # 2) 多因子归因
        expl = self.call_tool(
            "explain_degradation",
            {"vehicle_id": vid, "concern": "general"}, ctx)
        factors: list[dict[str, Any]] = []
        attribution_summary = ""
        if not expl.get("error"):
            expl_data = expl.get("data") or {}
            factors = expl_data.get("top_factors", []) or []
            attribution_summary = expl_data.get("summary", "") or ""

        # 3) 数据源 / 置信度（取最差来源）
        ds = worst_source(pred.get("data_source"), expl.get("data_source"))
        confidence = self.confidence_from_source(ds)

        # 4) 组装人读答案
        interval = ""
        if lo is not None and hi is not None:
            interval = f"（95% 预测区间 {lo}%–{hi}%）"
        factor_lines = ""
        if factors:
            lines = []
            for i, f in enumerate(factors, 1):
                lines.append(
                    f"  {i}. {f.get('name', f.get('factor', ''))}"
                    f"（权重 {f.get('weight', 0):.0%}）：{f.get('evidence', '')}"
                    f"——建议：{f.get('action', '')}")
            factor_lines = "\n".join(lines)
        answer = (
            f"车辆 {vid} 当前电池健康度（SOH）约 {current}%，"
            f"未来 {horizon} 天预测约 {predicted}%{interval}，风险等级：{risk}。"
        )
        if attribution_summary:
            answer += f"\n{attribution_summary}"
        if factor_lines:
            answer += f"\n主要衰减因素：\n{factor_lines}"
        answer += (
            "\n\n说明：以上为基于历史数据的趋势推演，并非已发生故障，"
            "具体电池状态应以线下技师实车检测（含 BMS 诊断与单体均衡）为准。"
        )
        if not calibrated and sigma is not None:
            answer += (
                f"\n（预测区间由留出误差 σ={sigma} 推导，尚未做严格校准，"
                "勿当作精确覆盖率保证。）"
            )

        caveats = ["趋势推演，非已发生故障，需线下技师确认"]
        status = "ok"
        if ds in ("mock", "unavailable"):
            status = "degraded"
            caveats.append(f"数据来源 {ds}，结论可信度有限")

        structured = {
            "vehicle_id": vid,
            "current_soh_pct": current,
            "predicted_soh_pct": predicted,
            "soh_pi95_low_pct": lo,
            "soh_pi95_high_pct": hi,
            "risk_level": risk,
            "horizon_days": horizon,
            "sigma_soh": sigma,
            "calibrated": calibrated,
            "top_factors": factors,
            "attribution_summary": attribution_summary,
            "data_source": ds,
            "confidence": confidence,
            "model_version": pred_data.get("model_version"),
        }
        return AgentResult(
            agent=self.name,
            status=status,
            answer=answer,
            structured=structured,
            caveats=caveats,
            tool_calls=[self.tool_call_entry(pred), self.tool_call_entry(expl)],
        )
