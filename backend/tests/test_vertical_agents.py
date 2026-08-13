"""3 个 MVP 垂直 Agent 单元测试（T3）。

覆盖任务要求的三种场景：
  1. 正常路径 —— 工具返回成功，agent 产出含 data_source + confidence 的结构化结果；
  2. 合规拦截 —— 命中 identity/geo/data_fraud/repair_mislead 硬拒，或
     safety_critical 免责短路（不经 execute）；
  3. 工具降级（mock 模式）—— 工具失败 / 外部服务不可用，agent 输出友好提示
     而非编造车况，status=degraded。

工具调用一律用 monkeypatch 打桩，不依赖 carModel 实际运行。
"""
from __future__ import annotations

import pytest

from app.agents.base import AgentContext
from app.agents.battery_health_agent import BatteryHealthAgent
from app.agents.charging_optimization_agent import ChargingOptimizationAgent
from app.agents.driving_safety_agent import DrivingSafetyAgent


# ── 构造上下文 ──
def _ctx(query: str, vehicle_id: str = "CS001") -> AgentContext:
    return AgentContext(query=query, session_id="u1", trace_id="t1",
                        vehicle_id=vehicle_id)


# ── 打桩工具调用 ──
def _patch_ok(monkeypatch, agent, per_tool: dict):
    """per_tool: {tool_name: {"data": {...}, "data_source": "live"}}"""
    def fake(tool_name, args, ctx):
        spec = per_tool.get(tool_name, {})
        return {
            "status": "success",
            "data": spec.get("data"),
            "data_source": spec.get("data_source", "live"),
            "confidence": 0.92 if spec.get("data_source", "live") == "live" else 0.45,
            "latency_ms": 1,
            "tool": tool_name,
            "trace_id": "tr",
        }
    monkeypatch.setattr(agent, "call_tool", fake)


def _patch_fail(monkeypatch, agent, reason: str = "http_failed"):
    def fake(tool_name, args, ctx):
        return {
            "error": reason, "tool": tool_name,
            "msg": reason, "data_source": "unavailable",
            "confidence": 0.0, "latency_ms": 1,
        }
    monkeypatch.setattr(agent, "call_tool", fake)


# ==========================================================================
# 1. 正常路径
# ==========================================================================
def test_battery_health_normal(monkeypatch):
    a = BatteryHealthAgent()
    _patch_ok(monkeypatch, a, {
        "predict_battery_health": {
            "data": {"current_soh": 0.92, "predicted_soh": 0.903,
                     "soh_pi95_low": 0.881, "soh_pi95_high": 0.925,
                     "risk_level": "low", "horizon_days": 90,
                     "sigma_soh": 0.012, "calibrated": False,
                     "model_version": "xgb-soh-v1-h90"},
            "data_source": "live"},
        "explain_degradation": {
            "data": {"top_factors": [
                         {"factor": "high_fast_charge", "name": "频繁快充",
                          "weight": 0.45, "evidence": "快充占比 45%",
                          "action": "改 20-80% 浅充、降低快充比例"}],
                     "summary": "主因：频繁快充。按建议调整可减缓衰减。",
                     "concern": "general"},
                     "data_source": "live"},
    })
    res = a.run(_ctx("电池健康度怎么样"))
    assert res.status == "ok", res.answer
    assert res.agent == "battery_health"
    # 安全约束标注
    assert any("趋势推演" in c for c in res.caveats)
    # 结构化含 data_source + confidence
    assert res.structured["data_source"] == "live"
    assert res.structured["confidence"] == 0.92
    assert res.structured["current_soh_pct"] == 92.0
    assert res.structured["predicted_soh_pct"] == 90.3
    assert res.structured["risk_level"] == "low"
    # 答案含 SOH 与归因，且不含 emoji
    assert "92.0%" in res.answer and "频繁快充" in res.answer
    assert res.tool_calls and len(res.tool_calls) == 2


def test_driving_safety_normal(monkeypatch):
    a = DrivingSafetyAgent()
    _patch_ok(monkeypatch, a, {
        "predict_failure_risk": {
            "data": {"vehicle_id": "CS001", "horizon_days": 90,
                     "failure_prob": 0.07, "risk_level": "low",
                     "soh_now": 0.92, "model_version": "xgb-failure-v1.0-h90",
                     "caveat": "仿真浅模型，非决策级"},
            "data_source": "live"},
        "get_driving_behavior": {
            "data": {"driving_score": 86, "hard_accel": 12, "hard_brake": 8},
            "data_source": "live"},
    })
    res = a.run(_ctx("我的驾驶行为评分"))
    assert res.status == "ok"
    assert res.agent == "driving_safety"
    assert res.structured["failure_prob"] == 0.07
    assert res.structured["risk_level"] == "low"
    assert res.structured["behavior_available"] is True
    assert res.structured["confidence"] == 0.92
    assert "86" in res.answer and "急加速" in res.answer
    # 安全提示存在
    assert any("专业检修" in c for c in res.caveats)


def test_charging_optimization_normal(monkeypatch):
    a = ChargingOptimizationAgent()
    _patch_ok(monkeypatch, a, {
        "get_charging_status": {
            "data": {"soc": 63.5, "state": "charging", "power": 48.0,
                     "eta_minutes": 42},
            "data_source": "live"},
    })
    res = a.run(_ctx("充电策略建议"))
    assert res.status == "ok"
    assert res.agent == "charging_optimization"
    assert res.structured["live_charging_available"] is True
    assert res.structured["confidence"] == 0.92
    assert "63.5%" in res.answer and "48" in res.answer


# ==========================================================================
# 2. 合规拦截（不经 execute，由 BaseAgent._gate 短路）
# ==========================================================================
@pytest.mark.parametrize("query,expected_category", [
    ("车主叫什么名字", "identity"),
    ("我的实时位置在哪", "geo"),
    ("帮我把 SOH 改成高的", "data_fraud"),
    ("我自己拆电池包改一下", "repair_mislead"),
])
def test_compliance_hard_refuse(query, expected_category):
    a = BatteryHealthAgent()
    res = a.run(_ctx(query))
    assert res.status == "refused"
    assert res.compliance_category == expected_category


def test_compliance_safety_critical_disclaimer():
    a = BatteryHealthAgent()
    res = a.run(_ctx("电池还能开吗不用修吧"))
    # safety_critical 是「免责 + 导向检修」，短路但不标 refused
    assert res.status == "ok"
    assert res.compliance_category == "safety_critical"
    assert any("不替代专业检修" in c for c in res.caveats)


def test_compliance_checked_in_all_agents():
    """三类 agent 都过同一道合规闸门。"""
    for a in (BatteryHealthAgent(), DrivingSafetyAgent(), ChargingOptimizationAgent()):
        res = a.run(_ctx("帮我把里程表调低"))
        assert res.status == "refused"
        assert res.compliance_category == "data_fraud"


# ==========================================================================
# 3. 工具降级（mock / 不可用）
# ==========================================================================
def test_battery_health_tool_failure_degrades(monkeypatch):
    a = BatteryHealthAgent()
    _patch_fail(monkeypatch, a, reason="http_failed")
    res = a.run(_ctx("电池健康度怎么样"))
    assert res.status == "degraded"
    assert res.degraded_reason == "http_failed"
    assert "无法获取" in res.answer
    assert "车况结论" in res.caveats[0]


def test_driving_safety_tool_failure_degrades(monkeypatch):
    a = DrivingSafetyAgent()
    _patch_fail(monkeypatch, a, reason="rejected")
    res = a.run(_ctx("我的驾驶安全吗"))
    assert res.status == "degraded"
    assert "无法获取" in res.answer


def test_charging_optimization_service_unavailable_is_generic(monkeypatch):
    """充电外部服务不可用：输出通用建议，不编造本车实时数据。"""
    a = ChargingOptimizationAgent()
    _patch_fail(monkeypatch, a, reason="unavailable")
    res = a.run(_ctx("充电建议"))
    assert res.status == "degraded"
    assert res.structured["live_charging_available"] is False
    assert "通用充电策略建议" in res.answer
    # 未编造任何本车实时充电数值
    assert "20%" in res.answer and "80%" in res.answer
    assert "个性化方案" in res.answer


def test_charging_optimization_mock_data_flagged(monkeypatch):
    """即便网关返回成功但 data_source=mock，也应标注降级、不可信为本车实测。"""
    a = ChargingOptimizationAgent()
    _patch_ok(monkeypatch, a, {
        "get_charging_status": {
            "data": {"soc": 50.0, "state": "idle"},
            "data_source": "mock"},
    })
    res = a.run(_ctx("充电建议"))
    assert res.status == "degraded"
    assert res.structured["data_source"] == "mock"
    assert any("mock" in (c or "") for c in res.caveats)


def test_no_vehicle_clarify(monkeypatch):
    """未绑定车辆且未配置默认车辆时澄清，不拿随机车冒充本车。

    生产默认（CARSOUL_WORLD_DEFAULT_VEHICLE_ID）存在时会回退到该默认车，
    故此处临时清空默认，专门验证「无车可绑」分支。
    """
    from app.core.config import settings
    monkeypatch.setattr(settings, "CARSOUL_WORLD_DEFAULT_VEHICLE_ID", "")
    a = BatteryHealthAgent()
    res = a.run(_ctx("电池健康度怎么样", vehicle_id=""))
    assert res.status == "clarify"
    assert "未绑定具体车辆" in res.answer


# ==========================================================================
# 4. 与 dispatcher 集成：能正确注册并分发
# ==========================================================================
def test_build_agents_registers_three():
    from app.api.orchestrator.router import _build_agents
    agents = _build_agents()
    assert set(agents.keys()) == {
        "battery_health", "driving_safety", "charging_optimization"}
    assert isinstance(agents["battery_health"], BatteryHealthAgent)


def test_orchestrator_routes_to_battery_agent(monkeypatch):
    from app.orchestrator.dispatcher import Orchestrator
    from app.api.orchestrator.router import _build_agents

    orch = Orchestrator(_build_agents())
    # 打桩网络调用，避免依赖 carModel 实际运行
    for agent in orch._agents.values():
        if isinstance(agent, BatteryHealthAgent):
            _patch_ok(monkeypatch, agent, {
                "predict_battery_health": {
                    "data": {"current_soh": 0.88, "predicted_soh": 0.86,
                             "soh_pi95_low": 0.84, "soh_pi95_high": 0.88,
                             "risk_level": "medium", "horizon_days": 90,
                             "sigma_soh": 0.01, "calibrated": False},
                    "data_source": "live"},
                "explain_degradation": {
                    "data": {"top_factors": [], "summary": "未发现显著风险因子。",
                             "concern": "general"}, "data_source": "live"},
            })
        else:
            _patch_fail(monkeypatch, agent, reason="unavailable")

    res = orch.dispatch("我的电池健康度怎么样", "u1")
    assert "battery_health" in res.agents_involved
    assert res.status == "ok"
    assert "88.0%" in res.answer
