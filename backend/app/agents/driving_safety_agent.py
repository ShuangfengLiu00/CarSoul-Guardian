"""驾驶安全垂直 Agent（MVP 启用）。

调用 carModel 风险类工具：``predict_failure_risk``（未来 H 天 catastrophic
故障概率 + 风险等级）作为主评估；并尝试 ``get_driving_behavior``（精细驾驶行为
画像：急加速/急刹车等）。后者属 tools_registry_ext 扩展工具，若网关未注册或
未接入则返回降级，本 Agent 退而用故障风险模型替代评估并如实说明，不编造行为分。

安全约束：任何风险评级都不能替代专业检修，输出必须带安全提示。

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

# 精细化驾驶行为画像的可能字段（get_driving_behavior 未实现时这些都不会出现）
_BEHAVIOR_FIELDS = (
    "driving_score", "score", "behavior_score", "safety_score",
    "hard_accel_count", "hard_brake_count", "hard_accel", "hard_brake",
    "risk_events", "fatigue_level", "aggression",
)


class DrivingSafetyAgent(VerticalAgentBase):
    name = "driving_safety"
    domain = "driving"
    tools = ["predict_failure_risk", "get_driving_behavior", "get_vehicle_state"]

    def parse(self, ctx: AgentContext) -> dict[str, Any]:
        return {"query": ctx.query}

    def _parse_behavior(self, data: dict) -> dict[str, Any]:
        """从 get_driving_behavior 返回里抽取可识别字段；无则视为不可用。"""
        if not isinstance(data, dict):
            return {}
        picked = {k: data[k] for k in _BEHAVIOR_FIELDS if k in data}
        return picked

    def execute(self, ctx: AgentContext, parsed: dict[str, Any]) -> AgentResult:
        vid = self.resolve_vehicle_id(ctx)
        if not vid:
            return self.no_vehicle_result()

        # 主评估：故障风险模型
        risk = self.call_tool(
            "predict_failure_risk",
            {"vehicle_id": vid, "horizon_days": 90}, ctx)
        if risk.get("error"):
            return self.degrade_result(vid, risk, "驾驶/故障风险评估")

        risk_data = risk.get("data") or {}
        prob = risk_data.get("failure_prob")
        level = risk_data.get("risk_level", "unknown")
        horizon = risk_data.get("horizon_days", 90)
        soh_now = risk_data.get("soh_now")
        caveat = risk_data.get("caveat", "")

        # 精细驾驶行为（扩展工具，可能未接入）
        beh = self.call_tool("get_driving_behavior", {"vehicle_id": vid}, ctx)
        behavior = self._parse_behavior(beh.get("data")) if not beh.get("error") else {}
        behavior_available = bool(behavior)

        # 数据源 / 置信度
        ds = worst_source(risk.get("data_source"), beh.get("data_source"))
        confidence = self.confidence_from_source(ds)

        # 组装答案
        prob_pct = f"{prob * 100:.1f}%" if isinstance(prob, (int, float)) else "未知"
        answer = (
            f"基于车辆 {vid} 的故障风险模型：未来 {horizon} 天发生 catastrophic "
            f"故障的概率为 {prob_pct}，风险等级：{level}。"
        )
        if isinstance(soh_now, (int, float)):
            answer += f"\n当前 SOH 约 {soh_to_pct(soh_now)}%（模型观测值）。"
        if behavior_available:
            beh_bits = []
            if "driving_score" in behavior or "score" in behavior:
                beh_bits.append(f"驾驶评分 {behavior.get('driving_score', behavior.get('score'))}")
            if "hard_accel" in behavior or "hard_accel_count" in behavior:
                beh_bits.append(
                    f"急加速 {behavior.get('hard_accel_count', behavior.get('hard_accel'))} 次")
            if "hard_brake" in behavior or "hard_brake_count" in behavior:
                beh_bits.append(
                    f"急刹车 {behavior.get('hard_brake_count', behavior.get('hard_brake'))} 次")
            if beh_bits:
                answer += "\n驾驶行为画像：" + "，".join(beh_bits) + "。"
        else:
            answer += (
                "\n（注：精细化驾驶行为评分——急加速/急刹车等——当前暂未接入，"
                "已用故障风险模型替代评估。）"
            )
        if caveat:
            answer += f"\n{caveat}"

        answer += (
            "\n\n安全提示：任何风险评级都不能替代专业检修。如车辆出现制动异常、"
            "电池鼓包/冒烟/焦味、转向失效或气囊故障灯常亮等征兆，请立即联系品牌授权"
            "售后或具备资质的机构实车检测；在检测结论出来前不要继续驾驶。"
        )

        status = "ok"
        caveats = ["风险评级非安全放行结论，需专业检修确认"]
        if not behavior_available:
            caveats.append("精细化驾驶行为评分暂未接入，结论基于故障风险模型")
        if ds in ("mock", "unavailable"):
            status = "degraded"
            caveats.append(f"数据来源 {ds}，结论可信度有限")

        structured = {
            "vehicle_id": vid,
            "failure_prob": prob,
            "risk_level": level,
            "horizon_days": horizon,
            "soh_now": soh_to_pct(soh_now) if isinstance(soh_now, (int, float)) else None,
            "behavior_available": behavior_available,
            "behavior": behavior,
            "data_source": ds,
            "confidence": confidence,
            "model_version": risk_data.get("model_version"),
        }
        return AgentResult(
            agent=self.name,
            status=status,
            answer=answer,
            structured=structured,
            caveats=caveats,
            tool_calls=[self.tool_call_entry(risk), self.tool_call_entry(beh)],
        )
