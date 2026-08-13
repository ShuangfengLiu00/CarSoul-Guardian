"""充电优化垂直 Agent（MVP 启用）。

调用 carModel charging 域工具（tools_registry_ext 的 ``get_charging_status`` /
``search_charging_stations`` / ``plan_charging_route``，经 adapters 降级）。

MVP 现实：第三方充电服务在 WARN-03 下默认不可用，工具会返回 degraded /
unavailable。此时本 Agent **不编造**任何本车实时充电数据，而是输出清晰标注的
「通用电池养护建议」，并说明接入实时充电网络后将升级为个性化方案。

安全 / 诚实纪律：未证明可用的数据绝不呈现为「本车实测」。
P0 铁律：无 emoji / 无紫粉渐变 / 无 AI 模板味文案 / 无硬编码颜色。
"""
from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext, AgentResult
from app.agents.vertical_base import VerticalAgentBase, worst_source

# 实时充电状态里可能识别的字段（第三方 mock/真实返回均不确定，全部防御性读取）
_STATUS_FIELDS = ("soc", "state", "charging_state", "power", "charging_power",
                 "eta_minutes", "eta", "station", "connector")


class ChargingOptimizationAgent(VerticalAgentBase):
    name = "charging_optimization"
    domain = "charging"
    tools = ["get_charging_status", "search_charging_stations", "plan_charging_route"]

    def parse(self, ctx: AgentContext) -> dict[str, Any]:
        return {"query": ctx.query}

    def _parse_status(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            return {}
        return {k: data[k] for k in _STATUS_FIELDS if k in data}

    def _generic_advice(self) -> str:
        """清晰标注的通用电池养护建议（非本车实测，绝不冒充实时数据）。"""
        return (
            "通用充电策略建议（基于电池养护常识，非针对本车的实时数据）：\n"
            "1. 日常保持电量在 20%–80% 区间（浅充浅放），避免长期满充或深度放电；\n"
            "2. 尽量减少直流快充频次，长途补能时快充至 80% 后切换慢充；\n"
            "3. 极端高/低温环境下充电前做好热管理，避免低温快充；\n"
            "4. 长期停放保持约 50% 电量并定期补电。\n\n"
            "说明：当前版本尚未接入实时充电网络（充电桩状态/沿途规划），"
            "以上为通用养护建议；接入后我将结合本车电量与周边站点给出个性化方案。"
        )

    def execute(self, ctx: AgentContext, parsed: dict[str, Any]) -> AgentResult:
        vid = self.resolve_vehicle_id(ctx)
        if not vid:
            return self.no_vehicle_result()

        # 实时充电状态（第三方，MVP 大概率 unavailable）
        status = self.call_tool("get_charging_status", {"vehicle_id": vid}, ctx)
        status_data = self._parse_status(status.get("data")) if not status.get("error") else {}

        # 周边站点（需位置；隐私策略下不持有实时位置，仅在有显式 slots 时尝试）
        stations = None
        location = (ctx.slots or {}).get("location")
        if location:
            st = self.call_tool(
                "search_charging_stations",
                {"location": location, "radius": 5000}, ctx)
            if not st.get("error"):
                stations = st.get("data")

        live_available = bool(status_data) or stations is not None

        # 数据源 / 置信度
        ds = worst_source(status.get("data_source"),
                          stations.get("data_source") if isinstance(stations, dict) else None)
        confidence = self.confidence_from_source(ds)

        if live_available:
            # 有实时数据：给出有针对性但保守的建议
            bits = []
            soc = status_data.get("soc")
            if isinstance(soc, (int, float)):
                bits.append(f"当前电量约 {round(soc, 1)}%")
            state = status_data.get("state") or status_data.get("charging_state")
            if state:
                bits.append(f"充电状态：{state}")
            power = status_data.get("power") or status_data.get("charging_power")
            if isinstance(power, (int, float)):
                bits.append(f"充电功率约 {round(power, 1)} kW")
            eta = status_data.get("eta_minutes") or status_data.get("eta")
            if isinstance(eta, (int, float)):
                bits.append(f"预计还需约 {round(eta)} 分钟充满")
            live_note = "，".join(bits) if bits else "已获取实时充电数据"
            answer = (
                f"已获取车辆 {vid} 的实时充电信息：{live_note}。\n"
                "建议：日常保持电量 20%–80%（浅充浅放）；尽量减少直流快充频次，"
                "长途补能时快充至 80% 后切换慢充；极端温度环境下充电前做好热管理。"
            )
            status_out = "ok"
            caveats: list[str] = []
            if ds in ("mock", "unavailable"):
                status_out = "degraded"
                caveats.append(f"数据来源 {ds}，建议可信度有限")
        else:
            # 降级：不编造，给通用建议
            answer = self._generic_advice()
            status_out = "degraded"
            caveats = [
                "实时充电网络未接入，以上为通用养护建议而非本车实测",
                "个性化充电方案需待充电服务接入后提供",
            ]
            confidence = self.confidence_from_source(ds, fallback=0.0)

        structured = {
            "vehicle_id": vid,
            "live_charging_available": live_available,
            "charging_status": status_data,
            "nearby_stations": stations,
            "data_source": ds,
            "confidence": confidence,
        }
        return AgentResult(
            agent=self.name,
            status=status_out,
            answer=answer,
            structured=structured,
            caveats=caveats,
            degraded_reason=(None if live_available else "charging_service_unavailable"),
            tool_calls=[self.tool_call_entry(status)],
        )
