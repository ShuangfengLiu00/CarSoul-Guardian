"""Tests for the CarSoul Agent package (TASK008).

Covers:
  - Main agent offline responses (backward compatible)
  - Five-sub-agent workflow: full anomaly chain
  - Normal branch (no anomalies → patrol report)
  - Trace log completeness (推理可追溯)
  - Guard boundary verification (no control tools)
  - Battery thermal demo scenario
"""
import sys
from pathlib import Path

import pytest

# Make the package importable when running tests directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from carsoul_agent.agents.carsoul_agent import CarSoulGuardianAgent  # noqa: E402
from carsoul_agent.agents.core import CoreWorkflow, build_core_workflow  # noqa: E402
from carsoul_agent.agents.core.state import AgentState, Trace  # noqa: E402
from carsoul_agent.config import settings as agent_settings  # noqa: E402
from carsoul_agent.tools import default_registry  # noqa: E402
from carsoul_agent.tools.guard_tools import action_store  # noqa: E402


@pytest.fixture()
def offline_agent(monkeypatch):
    """一个**确定**没有大模型的 Agent。

    构造环境里可能存在 OPENAI_API_KEY，那样 ``llm_enabled`` 会是 True，
    离线断言就会变得不确定。这里把 key 清空，确保"离线"名副其实。
    """
    monkeypatch.setattr(agent_settings, "openai_api_key", "", raising=False)
    return CarSoulGuardianAgent()


# ------------------------------------------------------------------ #
#  Backward-compatible smoke tests
# ------------------------------------------------------------------ #
def test_agent_offline_responds(offline_agent):
    """Main agent still works offline (no LLM key).

    离线时状态必须是 degraded。这里曾经断言 ``== "active"`` —— 那不是在
    保护正确行为，而是在**锁定**洗白链第七层（handle() 硬编码 active）：
    一个没有任何大模型的规则专家团被测试要求自称"运行中"。
    """
    result = offline_agent.handle(message="我的车需要保养吗", user="tester")
    assert result["agent_status"] == "degraded"
    assert result["llm_used"] is False
    assert result["llm_available"] is False
    assert result["llm_configured"] is False
    assert result["degraded"]["reason"] == "local_agent_no_llm_client"
    assert len(result["answer"]) > 0


def test_agent_health_query(offline_agent):
    """Health query triggers the workflow and returns a substantive answer."""
    result = offline_agent.handle(message="我的车健康状态怎么样", user="tester")
    # 同上：走的是规则工作流，没有任何大模型转述，只能报 degraded。
    assert result["agent_status"] == "degraded"
    assert result["llm_used"] is False
    assert result["route"] == "workflow"
    # The answer should mention the vehicle or a diagnosis.
    assert any(k in result["answer"] for k in ["Tesla", "守护", "风险", "健康"])


def test_agent_greeting(offline_agent):
    """Greeting returns a lightweight reply without the workflow."""
    result = offline_agent.handle(message="你好", user="tester")
    assert "CarSoul Guardian" in result["answer"]
    # 打招呼是纯模板，永远不该被算作"大模型在工作"。
    assert result["route"] == "greeting"
    assert result["llm_used"] is False
    assert result["agent_status"] == "degraded"


# ------------------------------------------------------------------ #
#  Five-sub-agent workflow tests
# ------------------------------------------------------------------ #
def test_workflow_battery_thermal_anomaly():
    """Battery thermal scenario runs the full 5-step closed loop."""
    action_store.clear()
    agent = CarSoulGuardianAgent()
    state = agent._build_initial_state("我的电池温度异常", "tester")
    result = CoreWorkflow.run(state)

    # Perception detected anomalies.
    assert result["is_normal"] is False
    assert len(result["anomalies"]) > 0

    # Diagnosis identified the root cause.
    diag = result["diagnosis"]["primary"]
    assert diag["root_cause"] == "电芯热失控早期征兆"
    assert diag["severity"] == "high"

    # Risk was quantified as urgent.
    risk = result["risk_assessment"]
    assert risk["level"] == "urgent"

    # Explainer produced user-facing text.
    assert len(result["explanation"]) > 0

    # Service agent fired guarded tools.
    suggestion = result["service_suggestion"]
    assert suggestion["priority"] == "high"
    assert len(suggestion["actions"]) > 0
    assert action_store.summary()["reminders"] >= 1
    assert action_store.summary()["lifecycle_events"] >= 1
    assert action_store.summary()["suggestions"] >= 1


def test_workflow_normal_branch():
    """When no anomalies are detected, the normal-report branch fires."""
    state: AgentState = {
        "vehicle_state": {
            "brand": "Tesla",
            "model": "Model Y",
            "mileage": 5000,
            "health_score": 95,
            "risks": [],
        },
        "driver_profile": {"driving_style": "balanced"},
        "sensor_window": [{"battery_temp": 30, "soc": 80, "health_score": 95}],
        "trace_log": [],
    }
    result = CoreWorkflow.run(state)

    assert result["is_normal"] is True
    assert "正常" in result["explanation"] or "巡检" in result["explanation"]
    assert result["service_suggestion"]["patrol_completed"] is True


def test_trace_log_complete():
    """The trace log captures every GOAI closed-loop step."""
    action_store.clear()
    agent = CarSoulGuardianAgent()
    state = agent._build_initial_state("电池温度过高", "tester")
    result = CoreWorkflow.run(state)

    trace = result["trace_log"]
    steps = [e["step"] for e in trace]

    # All five GOAI steps must be present.
    assert Trace.PERCEIVE in steps
    assert Trace.UNDERSTAND in steps
    assert Trace.REASON in steps
    assert Trace.TOOL in steps
    assert Trace.ACT in steps

    # The workflow completion marker must be present.
    assert "__complete__" in steps

    # Each trace entry has the required fields.
    for entry in trace:
        assert "step" in entry
        assert "agent" in entry
        assert "detail" in entry
        assert "timestamp" in entry


def test_workflow_path_anomaly():
    """Anomaly branch visits all five nodes in order."""
    action_store.clear()
    agent = CarSoulGuardianAgent()
    state = agent._build_initial_state("电池温度异常", "tester")
    result = CoreWorkflow.run(state)

    trace = result["trace_log"]
    complete_entry = [e for e in trace if e["step"] == "__complete__"][0]
    path = complete_entry["data"]["path"]

    assert path == ["perception", "diagnosis", "risk", "explainer", "service"]


def test_workflow_path_normal():
    """Normal branch skips diagnosis and risk."""
    state: AgentState = {
        "vehicle_state": {"brand": "Tesla", "model": "Model Y", "mileage": 1000, "risks": []},
        "driver_profile": {"driving_style": "eco"},
        "sensor_window": [{"battery_temp": 30, "soc": 90}],
        "trace_log": [],
    }
    result = CoreWorkflow.run(state)
    trace = result["trace_log"]
    complete_entry = [e for e in trace if e["step"] == "__complete__"][0]
    path = complete_entry["data"]["path"]

    assert path == ["perception", "explainer", "service"]


# ------------------------------------------------------------------ #
#  Guard boundary tests (守护非控制)
# ------------------------------------------------------------------ #
def test_no_control_tools_registered():
    """The tool registry must NOT contain any actuator-control tools."""
    all_tool_names = [t.name for t in default_registry.all()]
    forbidden = ["control_vehicle", "brake_control", "accelerate", "steer", "lock_door"]
    for name in forbidden:
        assert name not in all_tool_names, f"Forbidden tool '{name}' found in registry!"


def test_guarded_tools_exist():
    """The four guarded write tools must be registered."""
    assert default_registry.get("push_reminder") is not None
    assert default_registry.get("record_lifecycle_event") is not None
    assert default_registry.get("write_service_suggestion") is not None
    assert default_registry.get("create_service_order") is not None


def test_action_store_records_guarded_actions():
    """Guarded tool calls are recorded in the action store for audit."""
    action_store.clear()
    tool = default_registry.get("push_reminder")
    tool.run(vehicle_id=1, level="warning", title="test", message="test reminder")
    assert len(action_store.reminders) == 1
    assert action_store.reminders[0]["title"] == "test"


# ------------------------------------------------------------------ #
#  Sub-agent unit tests
# ------------------------------------------------------------------ #
def test_perception_detects_battery_temp():
    from carsoul_agent.agents.core.perception import PerceptionAgent

    agent = PerceptionAgent()
    state: AgentState = {
        "sensor_window": [{"battery_temp": 50, "soc": 80}],
        "vehicle_state": {},
        "trace_log": [],
    }
    result = agent.run(state)
    assert result["is_normal"] is False
    assert any(a["item"] == "电池温度" for a in result["anomalies"])


def test_diagnosis_matches_thermal_runaway():
    from carsoul_agent.agents.core.diagnosis import DiagnosisAgent

    agent = DiagnosisAgent()
    state: AgentState = {
        "anomalies": [{"category": "battery", "item": "电池温度", "level": "urgent"}],
        "trace_log": [],
    }
    result = agent.run(state)
    primary = result["diagnosis"]["primary"]
    assert primary["type"] == "battery_thermal"
    assert "热失控" in primary["root_cause"]


def test_risk_quantifies_severity():
    from carsoul_agent.agents.core.risk import RiskAgent

    agent = RiskAgent()
    state: AgentState = {
        "diagnosis": {
            "primary": {"severity": "high", "type": "battery_thermal", "confidence": 0.9},
            "secondary": [],
        },
        "trace_log": [],
    }
    result = agent.run(state)
    risk = result["risk_assessment"]
    assert risk["level"] == "urgent"
    assert risk["probability_percent"] == 80
    assert risk["eta_hours"] == 2


def test_explainer_adapts_to_driving_style():
    from carsoul_agent.agents.core.explainer import ExplainerAgent

    agent = ExplainerAgent()
    state: AgentState = {
        "is_normal": False,
        "vehicle_state": {"brand": "Tesla", "model": "Model Y"},
        "driver_profile": {"driving_style": "aggressive"},
        "diagnosis": {"primary": {"root_cause": "测试异常", "description": "测试描述"}},
        "risk_assessment": {"level": "warning", "eta_hours": 168, "probability_percent": 50},
        "trace_log": [],
    }
    result = agent.run(state)
    assert "安全" in result["explanation"] or "激进" in result["explanation"]


def test_service_fires_guarded_tools():
    from carsoul_agent.agents.core.service import ServiceAgent

    action_store.clear()
    agent = ServiceAgent()
    state: AgentState = {
        "is_normal": False,
        "vehicle_state": {"vehicle_id": 1},
        "diagnosis": {"primary": {"root_cause": "测试", "actions_hint": ["行动1"]}},
        "risk_assessment": {"level": "urgent", "probability_percent": 80},
        "explanation": "测试解释",
        "trace_log": [],
    }
    result = agent.run(state)
    assert result["service_suggestion"]["priority"] == "high"
    # Original push_reminder (1) + escalation Level 2 (first + escalated = 2) = 3
    assert action_store.summary()["reminders"] >= 1
    # Escalation Level 3 creates 3 service orders
    assert action_store.summary()["service_orders"] >= 1


# ------------------------------------------------------------------ #
#  Multi-agent expert panel tests (多智能体专家会诊)
# ------------------------------------------------------------------ #
def test_expert_panel_returns_five_opinions():
    """The expert panel convenes all five specialists."""
    from carsoul_agent.agents.core.experts import build_expert_panel, run_expert_panel

    panel = build_expert_panel()
    assert len(panel) == 5

    state: AgentState = {
        "anomalies": [{"category": "battery", "item": "电池温度", "level": "urgent"}],
        "vehicle_state": {},
        "driver_profile": {},
        "sensor_window": [],
        "trace_log": [],
    }
    opinions = run_expert_panel(state, experts=panel)
    assert len(opinions) == 5
    specialties = [o["specialty"] for o in opinions]
    assert "动力系统" in specialties
    assert "底盘系统" in specialties
    assert "电气系统" in specialties
    assert "驾驶行为" in specialties
    assert "保养规划" in specialties


def test_powertrain_expert_matches_thermal():
    """The powertrain expert claims battery-thermal anomalies."""
    from carsoul_agent.agents.core.experts import PowertrainExpert

    expert = PowertrainExpert()
    state: AgentState = {
        "anomalies": [{"category": "battery", "item": "电池温度", "level": "urgent"}],
        "vehicle_state": {},
        "driver_profile": {},
        "sensor_window": [],
        "trace_log": [],
    }
    opinion = expert.consult(state)
    assert opinion["specialty"] == "动力系统"
    assert opinion["finding_count"] >= 1
    assert any(f["type"] == "battery_thermal" for f in opinion["findings"])
    assert opinion["severity"] == "high"


def test_chassis_expert_matches_brake_wear():
    """The chassis expert claims brake-pad wear."""
    from carsoul_agent.agents.core.experts import ChassisExpert

    expert = ChassisExpert()
    state: AgentState = {
        "anomalies": [{"category": "brake", "item": "刹车片", "level": "warning"}],
        "vehicle_state": {},
        "driver_profile": {},
        "sensor_window": [],
        "trace_log": [],
    }
    opinion = expert.consult(state)
    assert opinion["finding_count"] >= 1
    assert any(f["type"] == "brake_pad_wear" for f in opinion["findings"])


def test_driving_expert_flags_aggressive_style():
    """The driving-behavior expert flags aggressive driving."""
    from carsoul_agent.agents.core.experts import DrivingBehaviorExpert

    expert = DrivingBehaviorExpert()
    state: AgentState = {
        "anomalies": [],
        "vehicle_state": {},
        "driver_profile": {"driving_style": "aggressive", "harsh_events": 15, "safety_score": 72},
        "sensor_window": [],
        "trace_log": [],
    }
    opinion = expert.consult(state)
    assert any(f["type"] == "aggressive_driving" for f in opinion["findings"])


def test_maintenance_expert_flags_due_service():
    """The maintenance expert flags an upcoming service interval."""
    from carsoul_agent.agents.core.experts import MaintenanceExpert

    expert = MaintenanceExpert()
    state: AgentState = {
        "anomalies": [],
        "vehicle_state": {"mileage": 49500, "health_score": 55},
        "driver_profile": {},
        "sensor_window": [],
        "trace_log": [],
    }
    opinion = expert.consult(state)
    assert any(f["type"] == "maintenance_due" for f in opinion["findings"])
    assert any(f["type"] == "general_health_decline" for f in opinion["findings"])


def test_diagnosis_includes_expert_opinions():
    """The diagnosis node surfaces expert opinions into state."""
    from carsoul_agent.agents.core.diagnosis import DiagnosisAgent

    agent = DiagnosisAgent()
    state: AgentState = {
        "anomalies": [{"category": "battery", "item": "电池温度", "level": "urgent"}],
        "vehicle_state": {},
        "driver_profile": {},
        "sensor_window": [],
        "trace_log": [],
    }
    result = agent.run(state)
    assert "expert_opinions" in result
    assert len(result["expert_opinions"]) == 10
    # The primary diagnosis is sourced from the powertrain expert.
    primary = result["diagnosis"]["primary"]
    assert primary["type"] == "battery_thermal"
    assert primary.get("specialty") == "动力系统"


def test_experts_isolated_from_failure():
    """A failing expert does not abort the panel."""
    from carsoul_agent.agents.core.experts import ExpertAgent, run_expert_panel

    class BrokenExpert(ExpertAgent):
        name = "broken"
        specialty = "故障专科"

        def consult(self, state):
            raise RuntimeError("boom")

    opinions = run_expert_panel({"anomalies": [], "trace_log": []}, experts=[BrokenExpert()])
    assert len(opinions) == 1
    assert opinions[0]["consulted"] is False


# ------------------------------------------------------------------ #
#  Three-level escalation closed loop tests (三级升级闭环 · P0-1)
# ------------------------------------------------------------------ #
def test_escalation_reaches_level_three():
    """The escalation chain reaches level 3 for urgent risks."""
    from carsoul_agent.agents.core.escalation import EscalationManager

    action_store.clear()
    mgr = EscalationManager()
    state = {
        "vehicle_state": {"vehicle_id": 1},
        "diagnosis": {"primary": {"root_cause": "电芯热失控早期征兆"}},
        "risk_assessment": {"level": "urgent", "probability_percent": 80},
        "explanation": "电池温度异常，存在热风险",
    }
    result = mgr.execute(state)
    assert result.level_reached == 3
    # Level 1 + Level 2 (2 steps) + Level 3 (3 services + 1 loop_closed) = 7
    chain_levels = [e["level"] for e in result.escalation_chain]
    assert 1 in chain_levels
    assert 2 in chain_levels
    assert 3 in chain_levels
    assert len(result.service_orders) == 3


def test_escalation_level2_has_two_notifications():
    """Level 2 produces a first notification and an escalated notification."""
    from carsoul_agent.agents.core.escalation import EscalationManager

    action_store.clear()
    mgr = EscalationManager()
    state = {
        "vehicle_state": {"vehicle_id": 1},
        "diagnosis": {"primary": {"root_cause": "测试异常"}},
        "risk_assessment": {"level": "warning", "probability_percent": 50},
        "explanation": "测试解释",
    }
    result = mgr.execute(state)
    level2_steps = [e for e in result.escalation_chain if e["level"] == 2]
    assert len(level2_steps) == 2
    assert level2_steps[0]["step"] == "first_notification"
    assert level2_steps[1]["step"] == "escalated_notification"


def test_escalation_service_orders_recorded():
    """Escalation Level 3 creates service orders in the action store."""
    from carsoul_agent.agents.core.escalation import EscalationManager

    action_store.clear()
    mgr = EscalationManager()
    state = {
        "vehicle_state": {"vehicle_id": 1},
        "diagnosis": {"primary": {"root_cause": "测试"}},
        "risk_assessment": {"level": "urgent", "probability_percent": 90},
        "explanation": "测试",
    }
    mgr.execute(state)
    assert action_store.summary()["service_orders"] == 3
    service_types = [o["service_type"] for o in action_store.service_orders]
    assert "roadside_assist" in service_types
    assert "manufacturer_service" in service_types
    assert "insurance_service" in service_types


def test_escalation_disabled_level3():
    """When level3 is disabled, escalation stops at level 2."""
    from carsoul_agent.agents.core.escalation import EscalationConfig, EscalationManager

    action_store.clear()
    config = EscalationConfig(level3_enabled=False)
    mgr = EscalationManager(config=config)
    state = {
        "vehicle_state": {"vehicle_id": 1},
        "diagnosis": {"primary": {"root_cause": "测试"}},
        "risk_assessment": {"level": "urgent", "probability_percent": 90},
        "explanation": "测试",
    }
    result = mgr.execute(state)
    assert result.level_reached == 2
    assert len(result.service_orders) == 0


def test_service_agent_returns_escalation_info():
    """The service agent surfaces escalation info in its output."""
    from carsoul_agent.agents.core.service import ServiceAgent

    action_store.clear()
    agent = ServiceAgent()
    state: AgentState = {
        "is_normal": False,
        "vehicle_state": {"vehicle_id": 1},
        "diagnosis": {"primary": {"root_cause": "电芯热失控", "actions_hint": ["靠边停车"]}},
        "risk_assessment": {"level": "urgent", "probability_percent": 85},
        "explanation": "电池热风险",
        "trace_log": [],
    }
    result = agent.run(state)
    escalation = result["service_suggestion"]["escalation"]
    assert escalation["level_reached"] == 3
    assert len(escalation["chain"]) >= 5
    assert len(escalation["service_orders"]) == 3


def test_create_service_order_tool_registered():
    """The create_service_order tool is in the registry and works."""
    action_store.clear()
    tool = default_registry.get("create_service_order")
    assert tool is not None
    r = tool.run(
        vehicle_id=1,
        service_type="roadside_assist",
        service_name="道路救援",
        priority="high",
        reason="测试",
    )
    assert r.ok
    assert r.data["service_type"] == "roadside_assist"
    assert action_store.summary()["service_orders"] == 1


def test_workflow_escalation_in_closed_loop():
    """The full workflow surfaces escalation info via closed_loop summary."""
    action_store.clear()
    agent = CarSoulGuardianAgent()
    result = agent.handle(message="电池温度异常", user="tester")
    closed_loop = result.get("closed_loop", {})
    escalation = closed_loop.get("escalation")
    assert escalation is not None
    assert escalation["level_reached"] == 3
    assert len(escalation["service_orders"]) == 3


# ------------------------------------------------------------------ #
#  RAG knowledge base integration tests (RAG 知识库接入 · P0-2)
# ------------------------------------------------------------------ #
class _MockLLMClient:
    """Mock LLM client that captures prompts and returns a canned response."""

    def __init__(self, response_content: str) -> None:
        from types import SimpleNamespace

        self._response = response_content
        self.captured_prompts: list[str] = []

        def _create(**kwargs: object) -> object:
            messages = kwargs.get("messages", [])  # type: ignore[arg-type]
            if messages:
                self.captured_prompts.append(messages[0].get("content", ""))  # type: ignore[union-attr]
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=self._response)
                    )
                ]
            )

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=_create))


# ------------------------------------------------------------------ #
#  诚实降级：agent_status 必须由真实 LLM 调用推导
#  （active 洗白链第七层的回归测试）
# ------------------------------------------------------------------ #
class _StubRetrievalCtx:
    """最小可用的 RAG 检索结果，用于驱动 knowledge 路径上的 LLM 分支。"""

    is_empty = False
    context_text = "知识库片段：机油更换周期通常为 1 万公里或一年。"
    results: list = []

    @staticmethod
    def sources() -> list[str]:
        return ["保养手册"]


class _StubKB:
    def retrieve(self, query: str, top_k: int = 4) -> _StubRetrievalCtx:
        return _StubRetrievalCtx()


class _FailingLLMClient:
    """调用必定抛异常的 client —— 模拟"配置了但链路实际不通"。"""

    def __init__(self) -> None:
        from types import SimpleNamespace

        def _create(**kwargs: object) -> object:
            raise RuntimeError("connection refused")

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=_create))


def test_tracked_client_counts_successful_calls():
    """代理在 chat.completions.create 收口点打点，覆盖整棵子专家调用树。"""
    from carsoul_agent.agents.carsoul_agent import _LLMCallRecorder, _TrackedLLMClient

    recorder = _LLMCallRecorder()
    client = _TrackedLLMClient(_MockLLMClient("ok"), recorder)
    assert recorder.succeeded == 0

    client.chat.completions.create(messages=[{"content": "hi"}])
    assert recorder.succeeded == 1
    assert recorder.failed == 0


def test_tracked_client_counts_failures_not_successes():
    """调用抛异常不算"用上了大模型"——那一轮回答其实是规则兜底产出的。"""
    from carsoul_agent.agents.carsoul_agent import _LLMCallRecorder, _TrackedLLMClient

    recorder = _LLMCallRecorder()
    client = _TrackedLLMClient(_FailingLLMClient(), recorder)

    with pytest.raises(RuntimeError):
        client.chat.completions.create(messages=[{"content": "hi"}])
    assert recorder.succeeded == 0
    assert recorder.failed == 1


def test_agent_reports_active_only_when_llm_really_answered():
    """反向验证：真的调通大模型时才报 active。

    没有这条，把 ``agent_status`` 恒定改成 "degraded" 也能让离线用例通过 ——
    那只是把谎言换了个方向。这里证明该字段确实跟随事实变化。
    """
    agent = CarSoulGuardianAgent()
    agent._kb = _StubKB()
    agent._client = agent._wrap_llm_client(_MockLLMClient("机油建议每 1 万公里更换。"))

    result = agent.handle(message="机油多久换一次", user="tester")
    assert result["route"] == "knowledge_rag"
    assert result["llm_used"] is True
    assert result["llm_available"] is True
    assert result["agent_status"] == "active"
    assert result["degraded"] is None
    assert result["llm_calls"]["succeeded"] == 1


def test_agent_degrades_when_llm_configured_but_call_fails():
    """配置了大模型 ≠ 大模型可用。调用失败必须如实降级。"""
    agent = CarSoulGuardianAgent()
    agent._kb = _StubKB()
    agent._client = agent._wrap_llm_client(_FailingLLMClient())

    result = agent.handle(message="机油多久换一次", user="tester")
    assert result["llm_configured"] is True
    assert result["llm_used"] is False
    assert result["llm_available"] is False
    assert result["agent_status"] == "degraded"
    assert result["degraded"]["reason"] == "local_agent_llm_call_failed"


def test_agent_status_not_carried_over_between_turns():
    """上一轮调通了不代表这一轮也调了 —— 计数器必须每轮清零。"""
    agent = CarSoulGuardianAgent()
    agent._kb = _StubKB()
    agent._client = agent._wrap_llm_client(_MockLLMClient("机油建议每 1 万公里更换。"))

    first = agent.handle(message="机油多久换一次", user="tester")
    assert first["agent_status"] == "active"

    # 打招呼是纯模板路径，不会调用大模型。
    second = agent.handle(message="你好", user="tester")
    assert second["route"] == "greeting"
    assert second["llm_used"] is False
    assert second["agent_status"] == "degraded"
    assert second["degraded"]["reason"] == "local_agent_rule_only_path"


def test_diagnosis_offline_knowledge_match():
    """Offline mode: diagnosis carries knowledge_match when context matches."""
    from carsoul_agent.agents.core.diagnosis import DiagnosisAgent

    agent = DiagnosisAgent()  # No LLM → offline mode
    state: AgentState = {
        "anomalies": [{"category": "battery", "item": "电池温度", "level": "urgent"}],
        "vehicle_state": {},
        "driver_profile": {},
        "sensor_window": [],
        "knowledge_context": "已知故障案例：电芯热失控早期征兆通常由散热系统异常引起。",
        "trace_log": [],
    }
    result = agent.run(state)
    primary = result["diagnosis"]["primary"]
    assert "knowledge_match" in primary
    assert primary["source"] == "rule_kb_matched"


def test_diagnosis_offline_no_match_without_context():
    """Offline mode: no knowledge_match when context is absent."""
    from carsoul_agent.agents.core.diagnosis import DiagnosisAgent

    agent = DiagnosisAgent()
    state: AgentState = {
        "anomalies": [{"category": "battery", "item": "电池温度", "level": "urgent"}],
        "vehicle_state": {},
        "driver_profile": {},
        "sensor_window": [],
        "trace_log": [],
    }
    result = agent.run(state)
    primary = result["diagnosis"]["primary"]
    assert "knowledge_match" not in primary


def test_diagnosis_offline_knowledge_match_description():
    """Offline mode: description keywords also match against knowledge context."""
    from carsoul_agent.agents.core.diagnosis import DiagnosisAgent

    agent = DiagnosisAgent()
    state: AgentState = {
        "anomalies": [{"category": "brake", "item": "刹车片", "level": "warning"}],
        "vehicle_state": {},
        "driver_profile": {},
        "sensor_window": [],
        "knowledge_context": "维护记录：刹车片磨损到达极限，需要更换制动衬片。",
        "trace_log": [],
    }
    result = agent.run(state)
    primary = result["diagnosis"]["primary"]
    assert "knowledge_match" in primary
    assert primary["source"] == "rule_kb_matched"


def test_diagnosis_llm_enrich_with_knowledge_context():
    """LLM mode: knowledge_context is injected into the enrichment prompt."""
    from carsoul_agent.agents.core.diagnosis import DiagnosisAgent

    mock_llm = _MockLLMClient(
        response_content=(
            '{"root_cause": "散热系统故障导致热失控", "confidence": 0.92, '
            '"reasoning": "知识库匹配", "knowledge_match": "匹配案例：散热泵失效"}'
        )
    )
    agent = DiagnosisAgent(llm_client=mock_llm)
    state: AgentState = {
        "anomalies": [{"category": "battery", "item": "电池温度", "level": "urgent"}],
        "vehicle_state": {"brand": "Tesla", "model": "Model Y", "mileage": 30000},
        "driver_profile": {},
        "sensor_window": [],
        "knowledge_context": "案例库：Tesla Model Y 散热泵失效导致电池过热。",
        "trace_log": [],
    }
    result = agent.run(state)
    primary = result["diagnosis"]["primary"]
    # LLM enrichment updated the root cause and confidence.
    assert primary["root_cause"] == "散热系统故障导致热失控"
    assert primary["confidence"] == 0.92
    assert primary["knowledge_match"] == "匹配案例：散热泵失效"
    assert primary["source"] == "llm_enriched_with_rag"
    # At least one captured prompt must contain the knowledge section.
    all_prompt_text = " ".join(mock_llm.captured_prompts)
    assert "知识库检索结果" in all_prompt_text
    assert "散热泵失效" in all_prompt_text


def test_expert_llm_enrich_with_knowledge_context():
    """Expert LLM enrichment injects knowledge_context into the prompt."""
    from carsoul_agent.agents.core.experts import PowertrainExpert

    mock_llm = _MockLLMClient(
        response_content=(
            '{"root_cause": "知识库修正根因", "confidence": 0.88, '
            '"reasoning": "匹配历史案例", "knowledge_match": "案例#102"}'
        )
    )
    expert = PowertrainExpert(llm_client=mock_llm)
    state: AgentState = {
        "anomalies": [{"category": "battery", "item": "电池温度", "level": "urgent"}],
        "vehicle_state": {"brand": "BYD", "model": "汉EV", "mileage": 20000},
        "driver_profile": {},
        "sensor_window": [],
        "knowledge_context": "BYD 汉EV 电池热失控案例集：案例#102 电芯内短路。",
        "trace_log": [],
    }
    opinion = expert.consult(state)
    assert opinion["finding_count"] >= 1
    top = opinion["findings"][0]
    assert top["root_cause"] == "知识库修正根因"
    assert top["knowledge_match"] == "案例#102"
    assert top["source"] == "llm_enriched_with_rag"
    # The prompt must include the knowledge section.
    assert len(mock_llm.captured_prompts) >= 1
    assert "相关知识库内容" in mock_llm.captured_prompts[0]
    assert "案例#102" in mock_llm.captured_prompts[0]


def test_workflow_knowledge_context_flows_through():
    """Full workflow: knowledge_context in state reaches the diagnosis node."""
    action_store.clear()
    agent = CarSoulGuardianAgent()
    state = agent._build_initial_state("电池温度异常", "tester")
    state["knowledge_context"] = "故障案例：电芯热失控早期征兆由散热异常引起。"
    result = CoreWorkflow.run(state)
    primary = result["diagnosis"]["primary"]
    assert "knowledge_match" in primary
    assert primary["source"] == "rule_kb_matched"
