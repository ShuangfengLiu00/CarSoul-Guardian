"""Tests for the CarSoul OS Runtime SDK (Step 5).

Verifies the Step 5 acceptance criteria:
  1. **≤20 lines** — an external script can run a custom car Agent
     in ≤20 lines of code.
  2. **Governance by default** — read-only tool whitelist is enforced
     by default; write tools are blocked.
  3. **Custom skills** — a custom Skill can be registered and executed
     without modifying framework code.
  4. **Memory hooks** — the SDK natively integrates with the memory
     engine; workflows record and recall memories.
  5. **Workflow execution** — execute_workflow produces a structured
     result with answer, anomalies, findings, and trace.
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

# Ensure project root is on the path.
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)
_VP = os.path.join(_BASE, "vehicle_protocol")
if _VP not in sys.path:
    sys.path.insert(0, _VP)

from kernel.runtime import (
    AgentWrapper,
    FORBIDDEN_TOOLS,
    GovernanceProfile,
    READ_TOOLS,
    SkillFinding,
    WRITE_TOOLS,
    create_agent,
    execute_workflow,
    get_skill_registry,
    register_skill,
    reset_skill_registry,
)
from kernel.runtime.governance import GovernanceProfile as GP


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #
@pytest.fixture(autouse=True)
def clean_skill_registry():
    """Clear the global skill registry before and after each test."""
    reset_skill_registry()
    yield
    reset_skill_registry()


@pytest.fixture
def frames():
    """Generate simulator frames for testing."""
    from simulator import create_virtual_vehicle
    from simulator.scenarios import cooling_fault_scenario

    sim = create_virtual_vehicle("family_ev", seed=42)
    return sim.run(days=365, scenario=cooling_fault_scenario())


@pytest.fixture
def single_frame(frames):
    """A single frame for simple tests."""
    return frames[-1]


# ------------------------------------------------------------------ #
#  1. Governance — read-only by default (acceptance criterion)
# ------------------------------------------------------------------ #
class TestGovernance:
    def test_default_is_read_only(self):
        """GovernanceProfile defaults to read-only."""
        g = GovernanceProfile()
        assert g.read_only is True

    def test_read_tools_allowed_by_default(self):
        """All read tools are allowed under the default profile."""
        g = GovernanceProfile()
        for tool in READ_TOOLS:
            assert g.is_tool_allowed(tool), f"Read tool {tool} should be allowed"

    def test_write_tools_blocked_by_default(self):
        """All write tools are blocked under the default profile."""
        g = GovernanceProfile()
        for tool in WRITE_TOOLS:
            allowed, reason = g.validate_tool(tool)
            assert not allowed, f"Write tool {tool} should be blocked"
            assert "只读" in reason or "写操作" in reason

    def test_forbidden_tools_always_blocked(self):
        """Forbidden tools are blocked even with read_only=False."""
        g = GovernanceProfile(read_only=False)
        for tool in FORBIDDEN_TOOLS:
            allowed, reason = g.validate_tool(tool)
            assert not allowed
            assert "禁止" in reason

    def test_write_tools_allowed_when_not_read_only(self):
        """Write tools are allowed when read_only=False."""
        g = GovernanceProfile(read_only=False)
        for tool in WRITE_TOOLS:
            assert g.is_tool_allowed(tool)

    def test_explicit_whitelist(self):
        """Explicit allowed_tools further restricts the whitelist."""
        g = GovernanceProfile(
            read_only=True,
            allowed_tools=["get_vehicle_info", "get_health_score"],
        )
        assert g.is_tool_allowed("get_vehicle_info")
        assert g.is_tool_allowed("get_health_score")
        assert not g.is_tool_allowed("get_alerts")  # not in explicit list

    def test_custom_forbidden(self):
        """Custom forbidden_tools are blocked."""
        g = GovernanceProfile(forbidden_tools=["get_alerts"])
        allowed, _ = g.validate_tool("get_alerts")
        assert not allowed

    def test_effective_allowed_excludes_forbidden(self):
        g = GovernanceProfile(read_only=False, forbidden_tools=["push_reminder"])
        effective = g.effective_allowed()
        assert "push_reminder" not in effective
        assert "get_vehicle_info" in effective


# ------------------------------------------------------------------ #
#  2. Skill registration and matching
# ------------------------------------------------------------------ #
class TestSkillRegistration:
    def test_register_skill(self):
        """A custom skill can be registered globally."""
        class MySkill:
            name = "test_skill"
            domain = "battery"
            def match(self, state):
                return True
            def run(self, state, tools, memory):
                return SkillFinding("battery", recommendation="test")

        skill = MySkill()
        register_skill(skill)
        assert get_skill_registry().get("test_skill") is skill

    def test_register_skill_via_decorator_pattern(self):
        """register_skill returns the skill for chaining."""
        class MySkill:
            name = "chain_skill"
            domain = "motor"
            def match(self, state):
                return False
            def run(self, state, tools, memory):
                return SkillFinding("motor")

        result = register_skill(MySkill())
        assert result.name == "chain_skill"

    def test_duplicate_registration_raises(self):
        """Registering a skill with the same name raises ValueError."""
        class SkillA:
            name = "dup_skill"
            domain = "battery"
            def match(self, state):
                return True
            def run(self, state, tools, memory):
                return SkillFinding("battery")

        register_skill(SkillA())
        with pytest.raises(ValueError, match="已注册"):
            register_skill(SkillA())

    def test_skill_must_have_name(self):
        """A skill without a name raises ValueError."""
        class NoName:
            domain = "battery"
            def match(self, state):
                return True
            def run(self, state, tools, memory):
                return SkillFinding("battery")

        with pytest.raises(ValueError, match="name"):
            register_skill(NoName())

    def test_skill_must_implement_match_and_run(self):
        """A skill without match/run raises ValueError."""
        class Incomplete:
            name = "incomplete"
            domain = "battery"

        with pytest.raises(ValueError, match="match"):
            register_skill(Incomplete())

    def test_unregister_skill(self):
        """A skill can be unregistered."""
        class MySkill:
            name = "temp_skill"
            domain = "battery"
            def match(self, state):
                return True
            def run(self, state, tools, memory):
                return SkillFinding("battery")

        register_skill(MySkill())
        assert get_skill_registry().unregister("temp_skill") is True
        assert get_skill_registry().get("temp_skill") is None


# ------------------------------------------------------------------ #
#  3. Agent creation
# ------------------------------------------------------------------ #
class TestCreateAgent:
    def test_create_agent_basic(self):
        """create_agent returns an AgentWrapper with correct config."""
        agent = create_agent("test_agent")
        assert isinstance(agent, AgentWrapper)
        assert agent.name == "test_agent"
        assert agent.governance.read_only is True

    def test_create_agent_with_skills(self):
        """Skills are registered on the agent."""
        class MySkill:
            name = "agent_skill"
            domain = "battery"
            def match(self, state):
                return True
            def run(self, state, tools, memory):
                return SkillFinding("battery")

        agent = create_agent("test_agent", skills=[MySkill()])
        assert len(agent.skills) == 1
        assert agent.skills[0].name == "agent_skill"

    def test_create_agent_with_custom_governance(self):
        """Custom governance profile is applied."""
        g = GovernanceProfile(read_only=False)
        agent = create_agent("test_agent", governance=g)
        assert agent.governance.read_only is False
        assert agent.is_tool_allowed("push_reminder")

    def test_create_agent_with_persistent_memory(self):
        """Agent can use a file-backed memory engine."""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test_agent.db")
        db_url = f"sqlite:///{db_path}"

        agent = create_agent("test_agent", memory=db_url)
        agent.remember("V001", "test_event")
        assert agent.memory_engine.count("V001") == 1
        agent.close()

        # Memory survives after the agent is closed.
        agent2 = create_agent("test_agent2", memory=db_url)
        assert agent2.memory_engine.count("V001") == 1
        agent2.close()

        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(tmpdir)

    def test_agent_validate_tool_read_only(self):
        """Agent with default governance blocks write tools."""
        agent = create_agent("test_agent")
        allowed, reason = agent.validate_tool("push_reminder")
        assert not allowed
        assert "只读" in reason or "写操作" in reason

    def test_agent_validate_tool_allowed(self):
        """Agent with default governance allows read tools."""
        agent = create_agent("test_agent")
        allowed, _ = agent.validate_tool("get_vehicle_info")
        assert allowed

    def test_agent_call_tool_governance_blocked(self):
        """call_tool blocks write tools under read-only governance."""
        agent = create_agent("test_agent")
        result = agent.call_tool("push_reminder", message="test")
        assert result["ok"] is False
        assert result["governance_blocked"] is True


# ------------------------------------------------------------------ #
#  4. Workflow execution
# ------------------------------------------------------------------ #
class TestExecuteWorkflow:
    def test_workflow_returns_result(self, frames):
        """execute_workflow returns a WorkflowResult."""
        agent = create_agent("test_agent")
        result = execute_workflow(agent, frames, "电池最近怎么样")
        assert result.agent_name == "test_agent"
        assert result.vehicle_id != ""
        assert len(result.answer) > 0
        assert result.soul_score > 0
        agent.close()

    def test_workflow_records_memories(self, frames):
        """Workflow records memories for detected anomalies."""
        agent = create_agent("test_agent")
        result = execute_workflow(agent, frames)
        assert result.memory_count > 0
        assert len(result.trace) > 0
        agent.close()

    def test_workflow_with_custom_skill(self, frames):
        """A custom skill is matched and executed during the workflow."""
        class BatteryCheckSkill:
            name = "battery_check_test"
            domain = "battery"
            def match(self, state):
                return "battery" in str(state.get("anomaly_topics", []))
            def run(self, state, tools, memory):
                return SkillFinding(
                    specialty="battery",
                    findings=[{"issue": "battery anomaly detected"}],
                    severity="warning",
                    recommendation="建议检查电池冷却系统",
                    confidence=0.9,
                )

        agent = create_agent("test_agent", skills=[BatteryCheckSkill()])
        result = execute_workflow(agent, frames, "电池怎么样")
        assert len(result.skill_findings) > 0
        finding = result.skill_findings[0]
        assert finding["specialty"] == "battery"
        assert "冷却" in finding["recommendation"]
        agent.close()

    def test_workflow_trace_has_steps(self, frames):
        """The workflow trace contains expected steps."""
        agent = create_agent("test_agent")
        result = execute_workflow(agent, frames)
        steps = [t["step"] for t in result.trace]
        assert "start" in steps
        assert "perceive" in steps
        assert "complete" in steps
        agent.close()

    def test_workflow_governance_violations_recorded(self, frames):
        """Write tool violations are recorded in the result."""
        agent = create_agent("test_agent")  # read-only by default
        result = execute_workflow(agent, frames)
        # The workflow audits write tools and records violations.
        assert len(result.governance_violations) > 0
        assert any("push_reminder" in v for v in result.governance_violations)
        agent.close()

    def test_workflow_answer_contains_soul_score(self, frames):
        """The answer mentions the soul score."""
        agent = create_agent("test_agent")
        result = execute_workflow(agent, frames)
        assert "灵魂指数" in result.answer
        agent.close()

    def test_workflow_answer_responds_to_query(self, frames):
        """The answer references the user's query."""
        agent = create_agent("test_agent")
        result = execute_workflow(agent, frames, "电池最近怎么样")
        assert "电池最近怎么样" in result.answer
        agent.close()

    def test_workflow_with_single_frame(self, single_frame):
        """Workflow works with a single frame, not just a list."""
        agent = create_agent("test_agent")
        result = execute_workflow(agent, single_frame)
        assert result.vehicle_id != ""
        assert len(result.answer) > 0
        agent.close()


# ------------------------------------------------------------------ #
#  5. Memory integration (native memory hooks)
# ------------------------------------------------------------------ #
class TestMemoryIntegration:
    def test_agent_remember_and_recall(self):
        """Agent can remember and recall via native memory hooks."""
        agent = create_agent("test_agent")
        agent.remember(
            "V001", "test_event",
            payload={"key": "value"},
            impact_target="battery_stress",
            impact_delta=0.3,
        )
        memories = agent.recall("V001")
        assert len(memories) == 1
        assert memories[0].event_type == "test_event"
        agent.close()

    def test_agent_memory_summary(self):
        """Agent can produce a memory summary."""
        agent = create_agent("test_agent")
        agent.remember(
            "V001", "fast_charge",
            impact_target="battery_stress",
            impact_delta=0.3,
        )
        summary = agent.memory_summary("V001")
        assert "车辆记忆概览" in summary.text
        agent.close()

    def test_workflow_memory_survives_restart(self, frames):
        """Memories recorded by the workflow survive agent restart."""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "restart_test.db")
        db_url = f"sqlite:///{db_path}"

        # First agent runs the workflow and records memories.
        agent1 = create_agent("test_agent", memory=db_url)
        execute_workflow(agent1, frames)
        count1 = agent1.memory_engine.count()
        assert count1 > 0
        agent1.close()

        # Second agent (same DB) can recall the memories.
        agent2 = create_agent("test_agent2", memory=db_url)
        count2 = agent2.memory_engine.count()
        assert count2 == count1
        agent2.close()

        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(tmpdir)


# ------------------------------------------------------------------ #
#  6. Acceptance: ≤20 line external script
# ------------------------------------------------------------------ #
class TestAcceptance20Lines:
    def test_external_script_under_20_lines(self, frames):
        """Acceptance: 外部脚本 ≤20 行跑起一个自定义汽车 Agent.

        This test mirrors what an external developer would write.
        The code below (between the markers) is exactly what the
        developer writes — no more than 20 lines.
        """
        # --- BEGIN EXTERNAL SCRIPT (≤20 lines) ---
        from carsoul_os import create_agent, register_skill, execute_workflow, GovernanceProfile, SkillFinding

        class BatterySkill:
            name = "battery_check"
            domain = "battery"
            def match(self, state):
                return "battery" in str(state.get("anomaly_topics", []))
            def run(self, state, tools, memory):
                return SkillFinding("battery", recommendation="检查电池冷却系统")

        agent = create_agent(name="my_guardian", skills=[BatterySkill()],
                             memory="sqlite:///:memory:",
                             governance=GovernanceProfile(read_only=True))
        result = execute_workflow(agent, frames, user_query="电池最近怎么样")
        # --- END EXTERNAL SCRIPT ---

        # Verify the script produced a valid result.
        assert result.agent_name == "my_guardian"
        assert len(result.answer) > 0
        assert "灵魂指数" in result.answer
        assert result.governance_violations  # governance enforced
        assert len(result.skill_findings) > 0  # custom skill ran
        agent.close()

    def test_governance_default_enforced(self, frames):
        """Acceptance: 治理约束经 SDK 默认生效（只读工具白名单）."""
        agent = create_agent("my_agent")  # default = read_only=True

        # All write tools must be blocked.
        for tool in WRITE_TOOLS:
            allowed, reason = agent.validate_tool(tool)
            assert not allowed, f"{tool} should be blocked by default"

        # All read tools must be allowed.
        for tool in READ_TOOLS:
            allowed, _ = agent.validate_tool(tool)
            assert allowed, f"{tool} should be allowed by default"

        agent.close()

    def test_custom_skill_without_framework_changes(self, frames):
        """Acceptance: 新增一个自定义 Skill 不改框架代码即可注册生效."""
        # This skill is defined entirely by the user — no framework
        # imports beyond the public API.
        class TirePressureSkill:
            name = "tire_pressure_monitor"
            domain = "chassis"
            def match(self, state):
                return "tire" in str(state.get("anomaly_topics", []))
            def run(self, state, tools, memory):
                return SkillFinding(
                    specialty="chassis",
                    findings=[{"issue": "tire pressure anomaly"}],
                    severity="warning",
                    recommendation="检查轮胎气压",
                    confidence=0.8,
                )

        # Register and use — no framework code changed.
        register_skill(TirePressureSkill())
        agent = create_agent("test_agent")
        result = execute_workflow(agent, frames)

        # The skill may or may not match depending on the frame,
        # but it should be registered without errors.
        assert get_skill_registry().get("tire_pressure_monitor") is not None
        agent.close()
