"""M1 量化指标基线测试（PRD §7 / M1-6）。

三块指标：
  1. 意图识别准确率 ≥ 92%  —— 确定性（不依赖 carModel，关闭 LLM 兜底保证可复现）。
  2. 工具调用成功率 ≥ 98%  —— 实时打 carModel 网关；carModel 不可达则跳过（不误报）。
  3. 复合任务闭环率 ≥ 90%  —— 实时跑 Orchestrator 全链路；carModel 不可达则跳过。

实时类测试统一用 pytest.mark.live，并在 carModel 不可达时 pytest.skip，
避免在 CI 无引擎环境下把「基础设施缺失」误判为「功能回归」。
"""
from __future__ import annotations

import os
import urllib.request

import pytest

from app.orchestrator.dispatcher import Orchestrator
from app.orchestrator.routing_table import (
    DISABLED_AGENT_REPLY, ENABLED_AGENTS, ROUTING_TABLE)

pytestmark = pytest.mark.live


# ── 1. 意图识别准确率（确定性）──────────────────────────────────────
# 标注集：(query, expected) —— expected ∈ ENABLED_AGENTS 或 "clarify"。
_INTENT_CASES = [
    # 电池健康（battery_health）
    ("电池健康度怎么样", "battery_health"),
    ("我的SOH还剩多少", "battery_health"),
    ("电池衰减快吗", "battery_health"),
    ("还剩多少寿命", "battery_health"),
    ("续航里程预测", "battery_health"),
    ("电池容量多少", "battery_health"),
    ("电池包状态", "battery_health"),
    ("帮我做一下衰减归因", "battery_health"),
    ("剩余寿命预估", "battery_health"),
    ("电池老化严重吗", "battery_health"),
    ("健康度趋势", "battery_health"),
    # 驾驶安全（driving_safety）
    ("驾驶安全评分", "driving_safety"),
    ("我有没有急刹车", "driving_safety"),
    ("急加速多吗", "driving_safety"),
    ("驾驶习惯怎么样", "driving_safety"),
    ("疲劳驾驶风险", "driving_safety"),
    ("驾驶行为分析", "driving_safety"),
    ("风险驾驶提醒", "driving_safety"),
    ("制动情况", "driving_safety"),
    # 充电优化（charging_optimization）
    ("充电策略建议", "charging_optimization"),
    ("快充好还是慢充好", "charging_optimization"),
    ("附近充电桩", "charging_optimization"),
    ("充电规划", "charging_optimization"),
    ("充电习惯怎么养成", "charging_optimization"),
    ("补能方案", "charging_optimization"),
    ("充电优化", "charging_optimization"),
    # 阶段 2 禁用 Agent（期望 clarify，不误路由到启用 Agent）
    ("保费多少", "clarify"),
    ("出险风险", "clarify"),
    ("理赔怎么报", "clarify"),
    ("残值评估", "clarify"),
    ("二手车值多少", "clarify"),
    ("保值率", "clarify"),
    # 完全越界（期望 clarify）
    ("今天天气怎么样", "clarify"),
    ("讲个笑话", "clarify"),
    ("帮我写首诗", "clarify"),
]


def _route_expected(orch: Orchestrator, q: str, expected: str) -> bool:
    intent = orch._identify_intent(q)
    if expected in ENABLED_AGENTS:
        return intent.agent_name == expected and intent.matched and not intent.disabled
    # clarify 期望：命中禁用 Agent，或未命中任何 Agent
    return bool(intent.disabled) or (not intent.matched)


def test_intent_accuracy(monkeypatch):
    """意图识别准确率 ≥ 92%（确定性，关闭 LLM 兜底避免非确定性）。"""
    # 关闭 LLM 兜底，隔离规则路由准确率
    monkeypatch.setattr(Orchestrator, "_llm_classify", lambda self, m: "")
    orch = Orchestrator(agents={})
    correct = sum(1 for q, exp in _INTENT_CASES if _route_expected(orch, q, exp))
    total = len(_INTENT_CASES)
    acc = correct / total
    # 失败样本便于定位
    misses = [(q, exp) for q, exp in _INTENT_CASES
              if not _route_expected(orch, q, exp)]
    assert acc >= 0.92, f"意图准确率 {acc:.2%} 低于 92%，失败样本：{misses}"
    assert total >= 30, "标注集样本不足，基线无代表性"


# ── 2 & 3. 实时：工具成功率 + 闭环率 ────────────────────────────────
def _carsoul_reachable() -> bool:
    base = os.environ.get("CARSOUL_WORLD_API_URL", "http://localhost:8000").rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


_LIVE_QUERIES = [
    "我的电池健康度怎么样，SOH 还剩多少",
    "驾驶安全评分怎么样，有没有急刹车",
    "充电有什么建议，充电策略怎么规划",
    # 复合（电池 + 驾驶，应串行双 Agent 闭环）
    "电池衰减和我的驾驶习惯有关系吗",
]


@pytest.fixture
def live_orch():
    if not _carsoul_reachable():
        pytest.skip("carModel :8000 不可达，跳过实时闭环测试")
    from app.api.orchestrator.router import _build_agents
    return Orchestrator(_build_agents())


def test_closed_loop_live(live_orch):
    """复合任务闭环率 ≥ 90%：每条查询都须完成（ok/degraded），不得 failed/crashed。"""
    completed, total = 0, 0
    for q in _LIVE_QUERIES:
        total += 1
        res = live_orch.dispatch(q, "m1-baseline", vehicle_id="CS001")
        # 闭环完成 = 非 failed、且产出了 answer；degraded（数据不足）也算完成
        if res.status != "failed" and res.answer.strip():
            completed += 1
    rate = completed / total
    assert rate >= 0.90, f"闭环率 {rate:.2%} 低于 90%（{completed}/{total}）"


def test_tool_success_live(live_orch):
    """工具调用成功率 ≥ 98%（实时网关；degraded 记为成功，failed 记为失败）。"""
    ok, total = 0, 0
    for q in _LIVE_QUERIES:
        res = live_orch.dispatch(q, "m1-baseline", vehicle_id="CS001")
        for sub in res.sub_results:
            for tc in sub.get("tool_calls", []):
                total += 1
                if tc.get("status") not in ("failed", "error", "rejected"):
                    ok += 1
    if total == 0:
        pytest.skip("无工具调用样本")
    rate = ok / total
    assert rate >= 0.98, f"工具成功率 {rate:.2%} 低于 98%（{ok}/{total}）"
