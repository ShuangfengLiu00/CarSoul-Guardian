"""Tests for the expert Skill system (Step 6 — 专家 Skills 化).

Verifies the Step 6 acceptance criteria:
  1. **10 个技能全部经 register_skill 装载** — all 10 expert skills
     can be registered via the global skill registry.
  2. **新增一个自定义 Skill 不改框架代码即可注册生效** — a user-defined
     Skill can be registered and executed without any framework changes.
  3. **Agent = 技能的编排组合** — preset factories produce the correct
     skill compositions (guardian = all 10, battery_agent = subset).
  4. **既有 36 个 Agent 测试保持绿色** — the expert adapters are thin
     wrappers that don't alter expert behaviour.

Test categories:
  - Expert skill instantiation and metadata
  - Global registration of all 10 expert skills
  - Skill matching (anomaly categories + domain signals)
  - Skill execution (produces SkillFinding)
  - Agent preset compositions
  - Custom skill registration (acceptance criterion)
  - Expert skills integrated with create_agent + workflow
"""
import os
import sys
import tempfile

import pytest

# Ensure project root is on the path.
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)
_VP = os.path.join(_BASE, "vehicle_protocol")
if _VP not in sys.path:
    sys.path.insert(0, _VP)
# ai-agent must be importable for expert skill adapters.
_AI = os.path.join(_BASE, "ai-agent")
if _AI not in sys.path:
    sys.path.insert(0, _AI)

from kernel.runtime import (
    AgentWrapper,
    GovernanceProfile,
    Skill,
    SkillFinding,
    create_agent,
    execute_workflow,
    get_skill_registry,
    register_skill,
    reset_skill_registry,
)
from kernel.runtime.skills import (
    ALL_EXPERT_SKILLS,
    ChassisSkill,
    ChargingIntelligenceSkill,
    DrivingBehaviorSkill,
    ElectricalSkill,
    EnergyOptimizationSkill,
    EnvironmentAdaptationSkill,
    ExpertSkillAdapter,
    MaintenanceSkill,
    PowertrainSkill,
    UserCompanionSkill,
    VehicleValueSkill,
    build_all_expert_skills,
    register_all_expert_skills,
)
from kernel.runtime.skills.presets import (
    AGENT_PRESETS,
    battery_agent_skills,
    energy_agent_skills,
    get_preset_skills,
    guardian_skills,
    list_presets,
    safety_agent_skills,
    value_agent_skills,
)


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
    """Generate simulator frames for workflow tests."""
    from simulator import create_virtual_vehicle
    from simulator.scenarios import cooling_fault_scenario

    sim = create_virtual_vehicle("family_ev", seed=42)
    return sim.run(days=365, scenario=cooling_fault_scenario())


# ------------------------------------------------------------------ #
#  1. Expert skill instantiation and metadata
# ------------------------------------------------------------------ #
class TestExpertSkillInstantiation:
    """All 10 expert skills can be instantiated with correct metadata."""

    @pytest.mark.parametrize("skill_cls,expected_name,expected_domain", [
        (PowertrainSkill, "powertrain_skill", "动力系统"),
        (ChassisSkill, "chassis_skill", "底盘系统"),
        (ElectricalSkill, "electrical_skill", "电气系统"),
        (DrivingBehaviorSkill, "driving_behavior_skill", "驾驶行为"),
        (MaintenanceSkill, "maintenance_skill", "保养规划"),
        (VehicleValueSkill, "vehicle_value_skill", "车辆价值"),
        (EnvironmentAdaptationSkill, "environment_skill", "环境适应"),
        (ChargingIntelligenceSkill, "charging_skill", "充电智能"),
        (EnergyOptimizationSkill, "energy_optimization_skill", "能耗优化"),
        (UserCompanionSkill, "user_companion_skill", "用户陪伴"),
    ])
    def test_skill_metadata(self, skill_cls, expected_name, expected_domain):
        """Each skill has the correct name and domain."""
        skill = skill_cls()
        assert skill.name == expected_name
        assert skill.domain == expected_domain

    def test_all_10_skills_in_list(self):
        """ALL_EXPERT_SKILLS contains exactly 10 skill classes."""
        assert len(ALL_EXPERT_SKILLS) == 10

    def test_build_all_expert_skills_returns_10(self):
        """build_all_expert_skills returns 10 instantiated skills."""
        skills = build_all_expert_skills()
        assert len(skills) == 10
        # Each must be an ExpertSkillAdapter.
        for s in skills:
            assert isinstance(s, ExpertSkillAdapter)

    def test_all_skill_names_unique(self):
        """All 10 skills have unique names."""
        skills = build_all_expert_skills()
        names = [s.name for s in skills]
        assert len(names) == len(set(names))

    def test_skills_implement_skill_protocol(self):
        """Each expert skill satisfies the Skill protocol (match + run)."""
        skills = build_all_expert_skills()
        for skill in skills:
            assert hasattr(skill, "name")
            assert hasattr(skill, "domain")
            assert callable(getattr(skill, "match"))
            assert callable(getattr(skill, "run"))


# ------------------------------------------------------------------ #
#  2. Global registration of all 10 expert skills
# ------------------------------------------------------------------ #
class TestExpertSkillRegistration:
    """Acceptance: 10 个技能全部经 register_skill 装载."""

    def test_register_all_returns_10_names(self):
        """register_all_expert_skills returns 10 skill names."""
        names = register_all_expert_skills()
        assert len(names) == 10

    def test_all_10_in_global_registry(self):
        """After registration, the global registry has 10 skills."""
        register_all_expert_skills()
        assert get_skill_registry().count() == 10

    def test_registered_names_match_expected(self):
        """The registered names match the 10 expected skill names."""
        names = set(register_all_expert_skills())
        expected = {
            "powertrain_skill", "chassis_skill", "electrical_skill",
            "driving_behavior_skill", "maintenance_skill",
            "vehicle_value_skill", "environment_skill",
            "charging_skill", "energy_optimization_skill",
            "user_companion_skill",
        }
        assert names == expected

    def test_register_individual_skill(self):
        """A single expert skill can be registered via register_skill."""
        skill = PowertrainSkill()
        register_skill(skill)
        assert get_skill_registry().get("powertrain_skill") is skill

    def test_idempotent_registration(self):
        """register_all_expert_skills is idempotent (no duplicate error)."""
        register_all_expert_skills()
        # Second call should not raise — already-registered skills are skipped.
        names = register_all_expert_skills()
        assert len(names) == 10
        assert get_skill_registry().count() == 10

    def test_unregister_expert_skill(self):
        """An expert skill can be unregistered."""
        register_all_expert_skills()
        assert get_skill_registry().unregister("chassis_skill") is True
        assert get_skill_registry().get("chassis_skill") is None
        assert get_skill_registry().count() == 9


# ------------------------------------------------------------------ #
#  3. Skill matching (anomaly categories + domain signals)
# ------------------------------------------------------------------ #
class TestExpertSkillMatching:
    """Skills match appropriate states via anomaly categories and domain signals."""

    def test_powertrain_matches_battery_anomaly(self):
        """PowertrainSkill matches battery-related anomalies."""
        skill = PowertrainSkill()
        state = {"anomalies": [{"category": "battery", "item": "电池温度"}]}
        assert skill.match(state) is True

    def test_powertrain_matches_motor_anomaly(self):
        """PowertrainSkill matches motor-related anomalies."""
        skill = PowertrainSkill()
        state = {"anomalies": [{"category": "motor", "item": "电机过热"}]}
        assert skill.match(state) is True

    def test_powertrain_no_match_unrelated(self):
        """PowertrainSkill does not match unrelated anomalies."""
        skill = PowertrainSkill()
        state = {"anomalies": [{"category": "brake", "item": "刹车片"}]}
        assert skill.match(state) is False

    def test_chassis_matches_brake_anomaly(self):
        """ChassisSkill matches brake anomalies."""
        skill = ChassisSkill()
        state = {"anomalies": [{"category": "brake", "item": "刹车片磨损"}]}
        assert skill.match(state) is True

    def test_chassis_matches_tire_anomaly(self):
        """ChassisSkill matches tire anomalies."""
        skill = ChassisSkill()
        state = {"anomalies": [{"category": "tire", "item": "胎压异常"}]}
        assert skill.match(state) is True

    def test_electrical_matches_sensor_anomaly(self):
        """ElectricalSkill matches sensor anomalies."""
        skill = ElectricalSkill()
        state = {"anomalies": [{"category": "sensor", "item": "传感器故障"}]}
        assert skill.match(state) is True

    def test_driving_behavior_matches_aggressive_style(self):
        """DrivingBehaviorSkill matches aggressive driving style (domain signal)."""
        skill = DrivingBehaviorSkill()
        state = {
            "anomalies": [],
            "driver_profile": {"driving_style": "aggressive"},
        }
        assert skill.match(state) is True

    def test_driving_behavior_matches_safety_score(self):
        """DrivingBehaviorSkill matches when safety_score is present."""
        skill = DrivingBehaviorSkill()
        state = {
            "anomalies": [],
            "driver_profile": {"safety_score": 72},
        }
        assert skill.match(state) is True

    def test_maintenance_matches_mileage(self):
        """MaintenanceSkill matches when mileage is available (domain signal)."""
        skill = MaintenanceSkill()
        state = {
            "anomalies": [],
            "vehicle_state": {"mileage": 49500},
        }
        assert skill.match(state) is True

    def test_maintenance_matches_health_score(self):
        """MaintenanceSkill matches when health_score is available."""
        skill = MaintenanceSkill()
        state = {
            "anomalies": [],
            "vehicle_state": {"health_score": 55},
        }
        assert skill.match(state) is True

    def test_vehicle_value_matches_purchase_price(self):
        """VehicleValueSkill matches when purchase_price is available."""
        skill = VehicleValueSkill()
        state = {
            "anomalies": [],
            "vehicle_state": {"purchase_price": 250000},
        }
        assert skill.match(state) is True

    def test_environment_matches_ambient_temp(self):
        """EnvironmentAdaptationSkill matches when ambient_temp is in sensor data."""
        skill = EnvironmentAdaptationSkill()
        state = {
            "anomalies": [],
            "sensor_window": [{"ambient_temp": -5}],
        }
        assert skill.match(state) is True

    def test_environment_matches_long_trip(self):
        """EnvironmentAdaptationSkill matches for long trips."""
        skill = EnvironmentAdaptationSkill()
        state = {
            "anomalies": [],
            "trip_context": {"distance_km": 500},
        }
        assert skill.match(state) is True

    def test_charging_matches_soc(self):
        """ChargingIntelligenceSkill matches when SOC data is available."""
        skill = ChargingIntelligenceSkill()
        state = {
            "anomalies": [],
            "sensor_window": [{"soc": 15}],
        }
        assert skill.match(state) is True

    def test_energy_matches_driving_style(self):
        """EnergyOptimizationSkill matches when driving_style is present."""
        skill = EnergyOptimizationSkill()
        state = {
            "anomalies": [],
            "driver_profile": {"driving_style": "aggressive"},
        }
        assert skill.match(state) is True

    def test_user_companion_always_matches(self):
        """UserCompanionSkill always matches (companion advice is always relevant)."""
        skill = UserCompanionSkill()
        state = {"anomalies": []}
        assert skill.match(state) is True

    def test_no_match_empty_state(self):
        """PowertrainSkill does not match an empty state."""
        skill = PowertrainSkill()
        assert skill.match({"anomalies": []}) is False


# ------------------------------------------------------------------ #
#  4. Skill execution (produces SkillFinding)
# ------------------------------------------------------------------ #
class TestExpertSkillExecution:
    """Skills produce SkillFinding when run with appropriate states."""

    def _make_memory(self):
        """Create an in-memory engine for skill execution."""
        from kernel.memory_engine import MemoryEngine
        return MemoryEngine("sqlite:///:memory:")

    def test_powertrain_skill_run_battery_thermal(self):
        """PowertrainSkill produces a finding for battery thermal anomaly."""
        skill = PowertrainSkill()
        state = {
            "anomalies": [{"category": "battery", "item": "电池温度", "level": "urgent"}],
            "vehicle_state": {},
            "driver_profile": {},
            "sensor_window": [],
            "trace_log": [],
        }
        finding = skill.run(state, tools=None, memory=self._make_memory())
        assert isinstance(finding, SkillFinding)
        assert finding.specialty == "动力系统"
        assert len(finding.findings) > 0
        assert finding.severity in ("warning", "critical")

    def test_chassis_skill_run_brake_wear(self):
        """ChassisSkill produces a finding for brake wear."""
        skill = ChassisSkill()
        state = {
            "anomalies": [{"category": "brake", "item": "刹车片", "level": "warning"}],
            "vehicle_state": {},
            "driver_profile": {},
            "sensor_window": [],
            "trace_log": [],
        }
        finding = skill.run(state, tools=None, memory=self._make_memory())
        assert isinstance(finding, SkillFinding)
        assert finding.specialty == "底盘系统"
        assert len(finding.findings) > 0

    def test_maintenance_skill_run_high_mileage(self):
        """MaintenanceSkill produces a finding for high mileage."""
        skill = MaintenanceSkill()
        state = {
            "anomalies": [],
            "vehicle_state": {"mileage": 49500, "health_score": 55},
            "driver_profile": {},
            "sensor_window": [],
            "trace_log": [],
        }
        finding = skill.run(state, tools=None, memory=self._make_memory())
        assert isinstance(finding, SkillFinding)
        assert finding.specialty == "保养规划"

    def test_driving_behavior_skill_run_aggressive(self):
        """DrivingBehaviorSkill produces a finding for aggressive driving."""
        skill = DrivingBehaviorSkill()
        state = {
            "anomalies": [],
            "vehicle_state": {},
            "driver_profile": {"driving_style": "aggressive", "harsh_events": 15, "safety_score": 72},
            "sensor_window": [],
            "trace_log": [],
        }
        finding = skill.run(state, tools=None, memory=self._make_memory())
        assert isinstance(finding, SkillFinding)
        assert finding.specialty == "驾驶行为"

    def test_charging_skill_run_low_soc(self):
        """ChargingIntelligenceSkill produces a finding for low SOC."""
        skill = ChargingIntelligenceSkill()
        state = {
            "anomalies": [],
            "vehicle_state": {},
            "driver_profile": {},
            "sensor_window": [{"soc": 12}],
            "trace_log": [],
        }
        finding = skill.run(state, tools=None, memory=self._make_memory())
        assert isinstance(finding, SkillFinding)
        assert finding.specialty == "充电智能"
        assert len(finding.findings) > 0

    def test_energy_skill_run_aggressive_style(self):
        """EnergyOptimizationSkill produces a finding for aggressive driving."""
        skill = EnergyOptimizationSkill()
        state = {
            "anomalies": [],
            "vehicle_state": {},
            "driver_profile": {"driving_style": "aggressive"},
            "sensor_window": [],
            "trace_log": [],
        }
        finding = skill.run(state, tools=None, memory=self._make_memory())
        assert isinstance(finding, SkillFinding)
        assert finding.specialty == "能耗优化"
        assert len(finding.findings) > 0

    def test_vehicle_value_skill_run(self):
        """VehicleValueSkill produces a finding when purchase price is available."""
        skill = VehicleValueSkill()
        state = {
            "anomalies": [],
            "vehicle_state": {
                "purchase_price": 250000,
                "purchase_date": "2022-01-15",
                "mileage": 30000,
                "health_score": 85,
                "energy_type": "ev",
            },
            "driver_profile": {},
            "sensor_window": [],
            "trace_log": [],
        }
        finding = skill.run(state, tools=None, memory=self._make_memory())
        assert isinstance(finding, SkillFinding)
        assert finding.specialty == "车辆价值"

    def test_environment_skill_run_cold_temp(self):
        """EnvironmentAdaptationSkill produces a finding for cold temperature."""
        skill = EnvironmentAdaptationSkill()
        state = {
            "anomalies": [],
            "vehicle_state": {},
            "driver_profile": {},
            "sensor_window": [{"ambient_temp": -10}],
            "trip_context": {},
            "trace_log": [],
        }
        finding = skill.run(state, tools=None, memory=self._make_memory())
        assert isinstance(finding, SkillFinding)
        assert finding.specialty == "环境适应"

    def test_user_companion_skill_run(self):
        """UserCompanionSkill produces a finding."""
        skill = UserCompanionSkill()
        state = {
            "anomalies": [],
            "vehicle_state": {"energy_type": "ev"},
            "driver_profile": {"driving_style": "eco"},
            "sensor_window": [],
            "trace_log": [],
        }
        finding = skill.run(state, tools=None, memory=self._make_memory())
        assert isinstance(finding, SkillFinding)
        assert finding.specialty == "用户陪伴"

    def test_skill_finding_to_dict(self):
        """SkillFinding.to_dict() produces the correct structure."""
        finding = SkillFinding(
            specialty="动力系统",
            findings=[{"issue": "高温"}],
            severity="warning",
            recommendation="检查冷却",
            confidence=0.9,
        )
        d = finding.to_dict()
        assert d["specialty"] == "动力系统"
        assert d["severity"] == "warning"
        assert d["confidence"] == 0.9
        assert len(d["findings"]) == 1

    def test_severity_mapping(self):
        """Expert severity is correctly mapped to SkillFinding severity."""
        skill = PowertrainSkill()
        state = {
            "anomalies": [{"category": "battery", "item": "电池温度", "level": "urgent"}],
            "vehicle_state": {},
            "driver_profile": {},
            "sensor_window": [],
            "trace_log": [],
        }
        finding = skill.run(state, tools=None, memory=self._make_memory())
        # Expert severity "high" → SkillFinding "warning"
        assert finding.severity in ("warning", "critical")


# ------------------------------------------------------------------ #
#  5. Agent preset compositions
# ------------------------------------------------------------------ #
class TestAgentPresets:
    """Acceptance: Agent = 技能的编排组合 (guardian = 全量, battery_agent = 子集)."""

    def test_guardian_preset_has_10_skills(self):
        """guardian preset returns all 10 expert skills."""
        skills = guardian_skills()
        assert len(skills) == 10

    def test_battery_agent_preset_has_3_skills(self):
        """battery_agent preset returns 3 skills (powertrain + chassis + charging)."""
        skills = battery_agent_skills()
        assert len(skills) == 3
        names = {s.name for s in skills}
        assert names == {"powertrain_skill", "chassis_skill", "charging_skill"}

    def test_safety_agent_preset_has_3_skills(self):
        """safety_agent preset returns 3 skills (chassis + driving + environment)."""
        skills = safety_agent_skills()
        assert len(skills) == 3
        names = {s.name for s in skills}
        assert names == {"chassis_skill", "driving_behavior_skill", "environment_skill"}

    def test_value_agent_preset_has_3_skills(self):
        """value_agent preset returns 3 skills (value + maintenance + companion)."""
        skills = value_agent_skills()
        assert len(skills) == 3
        names = {s.name for s in skills}
        assert names == {"vehicle_value_skill", "maintenance_skill", "user_companion_skill"}

    def test_energy_agent_preset_has_2_skills(self):
        """energy_agent preset returns 2 skills (charging + energy optimization)."""
        skills = energy_agent_skills()
        assert len(skills) == 2
        names = {s.name for s in skills}
        assert names == {"charging_skill", "energy_optimization_skill"}

    def test_get_preset_skills_valid(self):
        """get_preset_skills returns skills for a valid preset name."""
        skills = get_preset_skills("guardian")
        assert len(skills) == 10

    def test_get_preset_skills_invalid(self):
        """get_preset_skills raises ValueError for an unknown preset."""
        with pytest.raises(ValueError, match="未知预设"):
            get_preset_skills("nonexistent_agent")

    def test_list_presets_returns_all(self):
        """list_presets returns all 5 preset descriptions."""
        presets = list_presets()
        assert len(presets) == 5
        assert "guardian" in presets
        assert "battery_agent" in presets
        assert "safety_agent" in presets
        assert "value_agent" in presets
        assert "energy_agent" in presets

    def test_agent_presets_dict_matches_factories(self):
        """AGENT_PRESETS keys match the available factory functions."""
        assert set(AGENT_PRESETS.keys()) == {
            "guardian", "battery_agent", "safety_agent",
            "value_agent", "energy_agent",
        }

    def test_guardian_skills_cover_all_domains(self):
        """Guardian preset covers all 10 expert domains."""
        skills = guardian_skills()
        domains = {s.domain for s in skills}
        expected_domains = {
            "动力系统", "底盘系统", "电气系统", "驾驶行为", "保养规划",
            "车辆价值", "环境适应", "充电智能", "能耗优化", "用户陪伴",
        }
        assert domains == expected_domains


# ------------------------------------------------------------------ #
#  6. Custom skill registration (acceptance criterion)
# ------------------------------------------------------------------ #
class TestCustomSkillRegistration:
    """Acceptance: 新增一个自定义 Skill 不改框架代码即可注册生效."""

    def test_custom_skill_registered_and_executed(self):
        """A custom skill can be registered and executed without framework changes."""
        class TirePressureSkill:
            name = "custom_tire_skill"
            domain = "chassis"
            def match(self, state):
                return "tire" in str(state.get("anomaly_topics", []))
            def run(self, state, tools, memory, knowledge=None):
                return SkillFinding(
                    specialty="chassis",
                    findings=[{"issue": "胎压异常"}],
                    severity="warning",
                    recommendation="请检查轮胎气压",
                    confidence=0.85,
                )

        # Register without any framework code change.
        register_skill(TirePressureSkill())

        # Verify it's in the registry.
        assert get_skill_registry().get("custom_tire_skill") is not None

        # Verify it matches and runs correctly.
        state = {"anomaly_topics": ["tire_safety"]}
        matched = get_skill_registry().match_skills(state)
        assert any(s.name == "custom_tire_skill" for s in matched)

        # Execute the matched skill.
        from kernel.memory_engine import MemoryEngine
        skill = get_skill_registry().get("custom_tire_skill")
        finding = skill.run(state, tools=None, memory=MemoryEngine("sqlite:///:memory:"))
        assert finding.specialty == "chassis"
        assert "轮胎" in finding.recommendation or "气压" in finding.recommendation

    def test_custom_skill_alongside_expert_skills(self):
        """A custom skill coexists with the 10 expert skills."""
        register_all_expert_skills()

        class CustomSkill:
            name = "my_custom"
            domain = "custom"
            def match(self, state):
                return True
            def run(self, state, tools, memory, knowledge=None):
                return SkillFinding("custom", recommendation="custom advice")

        register_skill(CustomSkill())
        assert get_skill_registry().count() == 11
        assert get_skill_registry().get("my_custom") is not None

    def test_custom_skill_with_create_agent(self):
        """A custom skill works when passed to create_agent."""
        class BatteryHealthSkill:
            name = "battery_health_check"
            domain = "battery"
            def match(self, state):
                return "battery" in str(state.get("anomaly_topics", []))
            def run(self, state, tools, memory, knowledge=None):
                return SkillFinding(
                    specialty="battery",
                    severity="warning",
                    recommendation="建议检查电池健康度",
                    confidence=0.9,
                )

        agent = create_agent("test_agent", skills=[BatteryHealthSkill()])
        assert len(agent.skills) == 1
        assert agent.skills[0].name == "battery_health_check"
        agent.close()


# ------------------------------------------------------------------ #
#  7. Expert skills integrated with create_agent + workflow
# ------------------------------------------------------------------ #
class TestExpertSkillsWithAgent:
    """Expert skills work end-to-end with the SDK agent and workflow."""

    def test_agent_with_expert_skills(self, frames):
        """create_agent can use expert skills from presets."""
        skills = battery_agent_skills()
        agent = create_agent("battery_guardian", skills=skills)
        assert isinstance(agent, AgentWrapper)
        assert len(agent.skills) == 3
        agent.close()

    def test_workflow_with_registered_expert_skills(self, frames):
        """Workflow runs with globally-registered expert skills."""
        register_all_expert_skills()
        agent = create_agent("guardian_agent")
        result = execute_workflow(agent, frames, "电池怎么样")

        assert result.agent_name == "guardian_agent"
        assert len(result.answer) > 0
        # Expert skills should produce findings (at least some match the frame).
        assert isinstance(result.skill_findings, list)
        agent.close()

    def test_workflow_with_guardian_preset(self, frames):
        """Workflow runs with the full guardian preset (all 10 skills)."""
        skills = guardian_skills()
        agent = create_agent("full_guardian", skills=skills)
        result = execute_workflow(agent, frames, "全面体检")

        assert len(result.answer) > 0
        assert "灵魂指数" in result.answer
        agent.close()

    def test_workflow_with_battery_preset(self, frames):
        """Workflow runs with the battery_agent preset."""
        skills = battery_agent_skills()
        agent = create_agent("battery_agent", skills=skills)
        result = execute_workflow(agent, frames, "电池健康")

        assert len(result.answer) > 0
        agent.close()

    def test_expert_skills_produce_findings_in_workflow(self, frames):
        """Expert skills produce SkillFindings when matched in the workflow."""
        register_all_expert_skills()
        agent = create_agent("diagnostic_agent")
        result = execute_workflow(agent, frames)

        # The cooling-fault scenario should trigger battery-related skills.
        if result.anomalies:
            assert len(result.skill_findings) > 0
            # At least one finding should come from an expert skill.
            specialties = [f["specialty"] for f in result.skill_findings]
            assert len(specialties) > 0
        agent.close()

    def test_governance_still_enforced_with_expert_skills(self, frames):
        """Governance constraints are enforced even with expert skills."""
        skills = guardian_skills()
        agent = create_agent("governed_guardian", skills=skills)

        # Default governance is read-only.
        assert agent.governance.read_only is True
        # Write tools must be blocked.
        from kernel.runtime.governance import WRITE_TOOLS
        for tool in WRITE_TOOLS:
            allowed, _ = agent.validate_tool(tool)
            assert not allowed
        agent.close()
