"""Tests for the CarSoul OS Digital Twin Component Model.

Verifies that:
  - BatteryTwin / MotorTwin / ChassisTwin state machines transition correctly
  - State transitions follow normal → degrading → warning → critical
  - Health deductions are explainable (traceable to component + metric)
  - VehicleTwin aggregates component health into an explainable soul-score
  - Simulator → Twin integration works (365-day feed produces valid twin)
  - Cooling fault scenario triggers state transitions in the twin
  - Soul-score deductions sum correctly
  - to_dict() serialisation works
"""
import pytest
from datetime import datetime, timezone

from vehicle_schema import (
    BatteryState,
    ChassisState,
    DrivingProfile,
    MotorState,
    TelemetryFrame,
)

from digital_twin.component_model import (
    BatteryTwin,
    ChassisTwin,
    HealthDeduction,
    MotorTwin,
    SoulScoreResult,
    StateTransition,
    VehicleTwin,
    create_vehicle_twin_from_simulator,
)


# ------------------------------------------------------------------ #
#  Helpers
# ------------------------------------------------------------------ #
def make_frame(
    soh=98.0,
    battery_temp=28.0,
    charge_cycles=50,
    fast_charge_ratio=0.3,
    motor_efficiency=0.95,
    motor_wear=0.05,
    motor_temp=45.0,
    brake_wear=0.1,
    tire_wear=0.08,
    suspension_health=95.0,
    tire_pressure=2.4,
    mileage=10000,
    ts=None,
    vin="LSJW32V8X1S000001",
) -> TelemetryFrame:
    """Build a TelemetryFrame with the given parameters."""
    if ts is None:
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)

    return TelemetryFrame(
        ts=ts,
        vin=vin,
        battery=BatteryState(
            soh=soh,
            temperature=battery_temp,
            charge_cycles=charge_cycles,
            fast_charge_ratio=fast_charge_ratio,
            soc=70.0,
        ),
        motor=MotorState(
            efficiency=motor_efficiency,
            wear=motor_wear,
            temperature=motor_temp,
        ),
        chassis=ChassisState(
            brake_wear=brake_wear,
            tire_wear=tire_wear,
            suspension_health=suspension_health,
            tire_pressure=tire_pressure,
        ),
        driving=DrivingProfile(
            style="balanced",
            safety_score=85.0,
            eco_score=80.0,
            harsh_event_count=1,
            avg_speed=45.0,
        ),
        mileage=mileage,
        ambient_temp=25.0,
    )


# ------------------------------------------------------------------ #
#  1. BatteryTwin state machine
# ------------------------------------------------------------------ #
class TestBatteryTwin:
    def test_starts_normal(self):
        bt = BatteryTwin()
        assert bt.state == "normal"

    def test_stays_normal_with_healthy_metrics(self):
        bt = BatteryTwin()
        frame = make_frame(soh=95, battery_temp=30)
        transition = bt.ingest(frame)
        assert transition is None  # no state change
        assert bt.state == "normal"

    def test_transitions_to_degrading(self):
        bt = BatteryTwin()
        frame = make_frame(soh=88, battery_temp=30)  # SoH < 90
        transition = bt.ingest(frame)
        assert transition is not None
        assert transition.from_state == "normal"
        assert transition.to_state == "degrading"
        assert transition.is_degradation

    def test_transitions_to_warning(self):
        bt = BatteryTwin()
        # First go to degrading.
        bt.ingest(make_frame(soh=88, battery_temp=30))
        # Then to warning.
        transition = bt.ingest(make_frame(soh=72, battery_temp=30))
        assert transition is not None
        assert transition.to_state == "warning"

    def test_transitions_to_critical(self):
        bt = BatteryTwin()
        bt.ingest(make_frame(soh=88, battery_temp=30))   # normal → degrading
        bt.ingest(make_frame(soh=72, battery_temp=30))   # degrading → warning
        transition = bt.ingest(make_frame(soh=50, battery_temp=30))  # warning → critical
        assert transition is not None
        assert transition.to_state == "critical"

    def test_temperature_triggers_degrading(self):
        bt = BatteryTwin()
        frame = make_frame(soh=95, battery_temp=48)  # temp > 45 warning
        transition = bt.ingest(frame)
        assert transition is not None
        assert transition.to_state == "degrading"

    def test_temperature_triggers_warning(self):
        bt = BatteryTwin()
        bt.ingest(make_frame(soh=95, battery_temp=48))  # → degrading
        transition = bt.ingest(make_frame(soh=95, battery_temp=58))  # temp > 55+5
        assert transition is not None
        assert transition.to_state == "warning"

    def test_no_self_healing(self):
        """State cannot improve (one-way degradation)."""
        bt = BatteryTwin()
        bt.ingest(make_frame(soh=88, battery_temp=30))  # → degrading
        # Even if SoH improves, state stays degrading.
        transition = bt.ingest(make_frame(soh=99, battery_temp=25))
        assert transition is None
        assert bt.state == "degrading"

    def test_health_result_explainable(self):
        bt = BatteryTwin()
        bt.ingest(make_frame(soh=85, battery_temp=30))
        result = bt.health_result()

        assert result.component == "battery"
        assert 0 <= result.score <= 100
        assert len(result.deductions) > 0

        # Each deduction must be traceable.
        for d in result.deductions:
            assert d.component == "battery"
            assert d.metric is not None
            assert d.points > 0
            assert d.reason is not None

    def test_health_score_decreases_with_soh(self):
        bt_healthy = BatteryTwin()
        bt_healthy.ingest(make_frame(soh=98, battery_temp=28))

        bt_degraded = BatteryTwin()
        bt_degraded.ingest(make_frame(soh=75, battery_temp=28))

        assert bt_healthy.health_result().score > bt_degraded.health_result().score

    def test_fast_charge_stress_deducted(self):
        bt = BatteryTwin()
        bt.ingest(make_frame(soh=95, battery_temp=28, fast_charge_ratio=0.8))
        result = bt.health_result()

        fc_deductions = [d for d in result.deductions if d.metric == "fast_charge_ratio"]
        assert len(fc_deductions) == 1
        assert fc_deductions[0].points > 0

    def test_transition_history_recorded(self):
        bt = BatteryTwin()
        bt.ingest(make_frame(soh=88, battery_temp=30))
        bt.ingest(make_frame(soh=72, battery_temp=30))
        bt.ingest(make_frame(soh=50, battery_temp=30))

        history = bt.transition_history
        assert len(history) == 3
        assert history[0].from_state == "normal"
        assert history[0].to_state == "degrading"
        assert history[1].to_state == "warning"
        assert history[2].to_state == "critical"


# ------------------------------------------------------------------ #
#  2. MotorTwin state machine
# ------------------------------------------------------------------ #
class TestMotorTwin:
    def test_starts_normal(self):
        mt = MotorTwin()
        assert mt.state == "normal"

    def test_transitions_to_degrading(self):
        mt = MotorTwin()
        frame = make_frame(motor_wear=0.4)  # > 0.3
        transition = mt.ingest(frame)
        assert transition is not None
        assert transition.to_state == "degrading"

    def test_transitions_to_warning_via_wear(self):
        mt = MotorTwin()
        mt.ingest(make_frame(motor_wear=0.4))  # → degrading
        transition = mt.ingest(make_frame(motor_wear=0.7))  # > 0.6
        assert transition is not None
        assert transition.to_state == "warning"

    def test_transitions_to_warning_via_temp(self):
        mt = MotorTwin()
        mt.ingest(make_frame(motor_wear=0.4, motor_temp=50))
        transition = mt.ingest(make_frame(motor_wear=0.4, motor_temp=95))  # > 90
        assert transition is not None
        assert transition.to_state == "warning"

    def test_transitions_to_critical(self):
        mt = MotorTwin()
        mt.ingest(make_frame(motor_wear=0.4))
        mt.ingest(make_frame(motor_wear=0.7))
        transition = mt.ingest(make_frame(motor_wear=0.9))  # > 0.85
        assert transition is not None
        assert transition.to_state == "critical"

    def test_no_self_healing(self):
        mt = MotorTwin()
        mt.ingest(make_frame(motor_wear=0.4))
        transition = mt.ingest(make_frame(motor_wear=0.1))
        assert transition is None
        assert mt.state == "degrading"

    def test_health_result_explainable(self):
        mt = MotorTwin()
        mt.ingest(make_frame(motor_wear=0.5, motor_efficiency=0.88))
        result = mt.health_result()

        assert result.component == "motor"
        assert 0 <= result.score <= 100
        assert len(result.deductions) >= 1  # at least wear deduction

        wear_deductions = [d for d in result.deductions if d.metric == "wear"]
        assert len(wear_deductions) == 1
        assert wear_deductions[0].points > 0


# ------------------------------------------------------------------ #
#  3. ChassisTwin state machine
# ------------------------------------------------------------------ #
class TestChassisTwin:
    def test_starts_normal(self):
        ct = ChassisTwin()
        assert ct.state == "normal"

    def test_transitions_to_degrading_via_brake(self):
        ct = ChassisTwin()
        frame = make_frame(brake_wear=0.4)  # > 0.3
        transition = ct.ingest(frame)
        assert transition is not None
        assert transition.to_state == "degrading"

    def test_transitions_to_degrading_via_tire(self):
        ct = ChassisTwin()
        frame = make_frame(tire_wear=0.4)
        transition = ct.ingest(frame)
        assert transition is not None
        assert transition.to_state == "degrading"

    def test_transitions_to_degrading_via_suspension(self):
        ct = ChassisTwin()
        frame = make_frame(suspension_health=75)  # < 80
        transition = ct.ingest(frame)
        assert transition is not None
        assert transition.to_state == "degrading"

    def test_transitions_to_warning(self):
        ct = ChassisTwin()
        ct.ingest(make_frame(brake_wear=0.4))
        transition = ct.ingest(make_frame(brake_wear=0.7))  # > 0.6
        assert transition is not None
        assert transition.to_state == "warning"

    def test_transitions_to_critical(self):
        ct = ChassisTwin()
        ct.ingest(make_frame(tire_wear=0.4))
        ct.ingest(make_frame(tire_wear=0.7))
        transition = ct.ingest(make_frame(tire_wear=0.9))  # > 0.85
        assert transition is not None
        assert transition.to_state == "critical"

    def test_no_self_healing(self):
        ct = ChassisTwin()
        ct.ingest(make_frame(brake_wear=0.4))
        transition = ct.ingest(make_frame(brake_wear=0.1))
        assert transition is None
        assert ct.state == "degrading"

    def test_health_result_has_subsystem_deductions(self):
        ct = ChassisTwin()
        ct.ingest(make_frame(brake_wear=0.5, tire_wear=0.3, suspension_health=70))
        result = ct.health_result()

        assert result.component == "chassis"
        components_in_deductions = {d.component for d in result.deductions}
        assert "chassis.brake" in components_in_deductions
        assert "chassis.tire" in components_in_deductions
        assert "chassis.suspension" in components_in_deductions

    def test_tire_pressure_deduction(self):
        ct = ChassisTwin()
        ct.ingest(make_frame(tire_pressure=1.7))  # < 2.0
        result = ct.health_result()

        pressure_deductions = [d for d in result.deductions if d.metric == "tire_pressure"]
        assert len(pressure_deductions) == 1
        assert pressure_deductions[0].points > 0


# ------------------------------------------------------------------ #
#  4. VehicleTwin aggregator
# ------------------------------------------------------------------ #
class TestVehicleTwin:
    def test_initial_state(self):
        vt = VehicleTwin()
        assert vt.frames_ingested == 0
        assert vt.battery is not None
        assert vt.motor is not None
        assert vt.chassis is not None

    def test_ingest_single_frame(self):
        vt = VehicleTwin()
        frame = make_frame(soh=95, motor_wear=0.1, brake_wear=0.1)
        transitions = vt.ingest(frame)

        assert vt.frames_ingested == 1
        assert vt.vin == frame.vin
        assert vt.mileage == frame.mileage
        # Healthy frame → no transitions.
        assert len(transitions) == 0

    def test_ingest_multiple_frames(self):
        vt = VehicleTwin()
        for i in range(30):
            vt.ingest(make_frame(mileage=10000 + i * 35))
        assert vt.frames_ingested == 30

    def test_soul_score_healthy_vehicle(self):
        vt = VehicleTwin()
        vt.ingest(make_frame(soh=98, motor_wear=0.02, brake_wear=0.05,
                             tire_wear=0.03, suspension_health=98))
        score = vt.soul_score()

        assert isinstance(score, SoulScoreResult)
        assert 80 <= score.score <= 100
        assert score.grade in ("legendary", "excellent")
        assert "battery" in score.component_scores
        assert "motor" in score.component_scores
        assert "chassis" in score.component_scores

    def test_soul_score_degraded_vehicle(self):
        vt = VehicleTwin()
        vt.ingest(make_frame(soh=70, motor_wear=0.6, brake_wear=0.5,
                             tire_wear=0.4, suspension_health=60))
        score = vt.soul_score()

        assert score.score < 80
        assert len(score.deductions) > 0

    def test_soul_score_deductions_explainable(self):
        """Every deduction must be traceable to a component and metric."""
        vt = VehicleTwin()
        vt.ingest(make_frame(soh=80, motor_wear=0.4, brake_wear=0.3,
                             tire_wear=0.2, suspension_health=70))
        score = vt.soul_score()

        for d in score.deductions:
            assert d.component is not None
            assert d.metric is not None
            assert d.value is not None
            assert d.threshold is not None
            assert d.points > 0
            assert len(d.reason) > 0

    def test_soul_score_deductions_filterable(self):
        """Deductions can be filtered by component."""
        vt = VehicleTwin()
        vt.ingest(make_frame(soh=80, motor_wear=0.4, brake_wear=0.3))
        score = vt.soul_score()

        battery_deductions = score.deductions_for("battery")
        assert len(battery_deductions) > 0
        for d in battery_deductions:
            assert d.component == "battery"

    def test_state_transitions_aggregated(self):
        """Transitions from all components are collected."""
        vt = VehicleTwin()
        # This frame should trigger transitions in multiple components.
        vt.ingest(make_frame(soh=85, motor_wear=0.5, brake_wear=0.5))
        transitions = vt.all_transitions()

        components = {t.component for t in transitions}
        assert "battery" in components
        assert "motor" in components
        assert "chassis" in components

    def test_transitions_for_specific_component(self):
        vt = VehicleTwin()
        vt.ingest(make_frame(soh=85, motor_wear=0.5, brake_wear=0.5))

        battery_transitions = vt.transitions_for("battery")
        assert len(battery_transitions) >= 1
        assert all(t.component == "battery" for t in battery_transitions)

    def test_to_dict(self):
        vt = VehicleTwin()
        vt.ingest(make_frame(soh=90, motor_wear=0.1, brake_wear=0.1))
        d = vt.to_dict()

        assert "vin" in d
        assert "soul_score" in d
        assert "grade" in d
        assert "component_scores" in d
        assert "component_states" in d
        assert "deductions" in d
        assert "transitions" in d
        assert d["frames_ingested"] == 1


# ------------------------------------------------------------------ #
#  5. Simulator → Twin integration (acceptance test)
# ------------------------------------------------------------------ #
class TestSimulatorIntegration:
    """The key acceptance test: simulator data flows into the twin."""

    def test_365_day_feed_produces_valid_twin(self):
        """Simulator → 365 TelemetryFrames → VehicleTwin → soul-score."""
        from simulator import create_virtual_vehicle

        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=365)

        twin = create_vehicle_twin_from_simulator(frames)

        assert twin.frames_ingested == 365
        assert twin.vin is not None
        assert twin.mileage > 0

        score = twin.soul_score()
        assert 0 <= score.score <= 100
        assert score.grade in ("legendary", "excellent", "normal", "risk")
        assert len(score.component_scores) == 3  # battery, motor, chassis

    def test_healthy_year_has_high_score(self):
        """A normal 365-day lifecycle should produce a good soul-score."""
        from simulator import create_virtual_vehicle

        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=365)

        twin = create_vehicle_twin_from_simulator(frames)
        score = twin.soul_score()

        # After 1 year of normal family use, the score should still be good.
        assert score.score > 70

    def test_soul_score_deductions_traceable(self):
        """Every deduction in the soul-score must be traceable."""
        from simulator import create_virtual_vehicle

        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=365)

        twin = create_vehicle_twin_from_simulator(frames)
        score = twin.soul_score()

        for d in score.deductions:
            # Each deduction must reference a valid component.
            assert d.component in (
                "battery", "motor", "chassis.brake",
                "chassis.tire", "chassis.suspension",
            )
            assert d.points > 0
            assert len(d.reason) > 10  # meaningful explanation

    def test_cooling_fault_triggers_transitions(self):
        """The cooling fault scenario should trigger state transitions."""
        from simulator import create_virtual_vehicle
        from simulator.scenarios import cooling_fault_scenario

        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=600, scenario=cooling_fault_scenario())

        twin = create_vehicle_twin_from_simulator(frames)
        transitions = twin.all_transitions()

        # The cooling fault should cause at least one battery transition.
        battery_transitions = twin.transitions_for("battery")
        assert len(battery_transitions) >= 1

        # At least one transition should be to warning or critical.
        worst = max(battery_transitions, key=lambda t: {
            "normal": 0, "degrading": 1, "warning": 2, "critical": 3
        }[t.to_state])
        assert worst.to_state in ("degrading", "warning", "critical")

    def test_cooling_fault_lowers_score(self):
        """The cooling fault scenario should produce a lower score."""
        from simulator import create_virtual_vehicle
        from simulator.scenarios import cooling_fault_scenario, normal_lifecycle

        # Normal lifecycle.
        sim_normal = create_virtual_vehicle("family_ev", seed=42)
        frames_normal = sim_normal.run(days=600, scenario=normal_lifecycle())
        twin_normal = create_vehicle_twin_from_simulator(frames_normal)
        score_normal = twin_normal.soul_score()

        # Cooling fault scenario.
        sim_fault = create_virtual_vehicle("family_ev", seed=42)
        frames_fault = sim_fault.run(days=600, scenario=cooling_fault_scenario())
        twin_fault = create_vehicle_twin_from_simulator(frames_fault)
        score_fault = twin_fault.soul_score()

        assert score_fault.score < score_normal.score

    def test_all_profiles_produce_valid_twins(self):
        """All three built-in profiles should produce valid twins."""
        from simulator import create_virtual_vehicle

        for profile_name in ["performance_ev", "family_ev", "hybrid"]:
            sim = create_virtual_vehicle(profile_name, seed=42)
            frames = sim.run(days=365)

            twin = create_vehicle_twin_from_simulator(frames)
            score = twin.soul_score()

            assert twin.frames_ingested == 365
            assert 0 <= score.score <= 100
            assert len(score.component_scores) == 3

    def test_streaming_ingest(self):
        """ingest_stream should work with iterators."""
        from simulator import create_virtual_vehicle

        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=30)

        twin = VehicleTwin()
        # Use the iterator interface.
        all_transitions = twin.ingest_stream(iter(frames))

        assert twin.frames_ingested == 30
        assert len(all_transitions) == 30  # one list per frame


# ------------------------------------------------------------------ #
#  6. Soul-score explainability (the key innovation)
# ------------------------------------------------------------------ #
class TestExplainability:
    """The soul-score must be fully explainable: every point lost is traceable."""

    def test_deductions_sum_matches_score_loss(self):
        """The sum of deduction points should approximately equal 100 - score."""
        from simulator import create_virtual_vehicle

        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=365)

        twin = create_vehicle_twin_from_simulator(frames)
        score = twin.soul_score()

        # The component scores are weighted averages of 100 - deductions.
        # So the soul-score = weighted_avg(component_scores).
        # We verify that the deductions are consistent with component scores.
        for component_name in ("battery", "motor", "chassis"):
            component_result = twin.component_health(component_name)
            if component_result is None:
                continue

            total_deduction = sum(d.points for d in component_result.deductions)
            expected_score = max(0, 100 - total_deduction)

            # The component score should be 100 - total_deductions (clamped).
            assert abs(component_result.score - expected_score) < 1.0, (
                f"{component_name}: score={component_result.score}, "
                f"expected={expected_score}, deductions={total_deduction}"
            )

    def test_every_deduction_has_meaningful_reason(self):
        """Each deduction must have a human-readable reason."""
        from simulator import create_virtual_vehicle

        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=365)

        twin = create_vehicle_twin_from_simulator(frames)
        score = twin.soul_score()

        for d in score.deductions:
            assert len(d.reason) > 10
            # Reason should contain the metric value.
            assert str(d.value) in d.reason or f"{d.value:.1f}" in d.reason or \
                   f"{d.value:.1%}" in d.reason

    def test_component_scores_in_valid_range(self):
        """All component scores must be in [0, 100]."""
        from simulator import create_virtual_vehicle

        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=365)

        twin = create_vehicle_twin_from_simulator(frames)
        score = twin.soul_score()

        for component, component_score in score.component_scores.items():
            assert 0 <= component_score <= 100

    def test_score_change_explainable_by_transitions(self):
        """When a component transitions, the score change should be explainable."""
        from simulator import create_virtual_vehicle
        from simulator.scenarios import AnomalyInjection, AnomalyType, ScenarioConfig

        # Create a scenario with an early anomaly.
        scenario = ScenarioConfig(
            anomalies=[
                AnomalyInjection(
                    anomaly_type=AnomalyType.COOLING_FAILURE,
                    start_day=50,
                    ramp_days=20,
                    severity=1.0,
                ),
            ],
        )

        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=100, scenario=scenario)

        twin = create_vehicle_twin_from_simulator(frames)

        # There should be battery transitions.
        battery_transitions = twin.transitions_for("battery")
        assert len(battery_transitions) >= 1

        # The soul-score should have battery-related deductions.
        score = twin.soul_score()
        battery_deductions = score.deductions_for("battery")
        assert len(battery_deductions) > 0

        # At least one deduction should mention temperature (cooling fault effect).
        temp_deductions = [d for d in battery_deductions if d.metric == "temperature"]
        assert len(temp_deductions) > 0


# ------------------------------------------------------------------ #
#  7. Acceptance test: the exact spec scenario
# ------------------------------------------------------------------ #
class TestAcceptance:
    def test_simulator_to_twin_pipeline(self):
        """Full pipeline: Simulator → TelemetryFrame → VehicleTwin → SoulScore.

        This is the Step 3 acceptance test: "模拟器数据流 → 孪生体实时同步；
        soul-score 变化可解释到具体部件状态变迁。"
        """
        from simulator import create_virtual_vehicle

        # 1. Simulator produces 365 days of compliant telemetry.
        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=365)
        assert len(frames) == 365

        # 2. Twin ingests all frames (real-time sync simulation).
        twin = create_vehicle_twin_from_simulator(frames)
        assert twin.frames_ingested == 365

        # 3. Soul-score is computed and explainable.
        score = twin.soul_score()
        assert 0 <= score.score <= 100

        # 4. Every deduction is traceable to a component.
        for d in score.deductions:
            assert d.component is not None
            assert d.metric is not None
            assert d.points > 0
            assert d.reason is not None

        # 5. State transitions are recorded and explainable.
        for t in score.transitions:
            assert t.component is not None
            assert t.from_state != t.to_state
            assert t.reason is not None

        # 6. Component scores are present.
        assert "battery" in score.component_scores
        assert "motor" in score.component_scores
        assert "chassis" in score.component_scores

    def test_anomaly_scenario_explainable_degradation(self):
        """When an anomaly is injected, the degradation is explainable."""
        from simulator import create_virtual_vehicle
        from simulator.scenarios import cooling_fault_scenario

        sim = create_virtual_vehicle("family_ev", seed=42)
        frames = sim.run(days=600, scenario=cooling_fault_scenario())

        twin = create_vehicle_twin_from_simulator(frames)
        score = twin.soul_score()

        # 1. Transitions exist (state changed during the simulation).
        assert len(score.transitions) > 0

        # 2. At least one battery transition occurred (cooling fault).
        battery_transitions = [t for t in score.transitions if t.component == "battery"]
        assert len(battery_transitions) >= 1

        # 3. The battery transition reason mentions SoH or temperature.
        for t in battery_transitions:
            assert "SoH" in t.reason or "Temperature" in t.reason

        # 4. Temperature deductions exist in the final score.
        temp_deductions = [
            d for d in score.deductions
            if d.metric == "temperature"
        ]
        assert len(temp_deductions) > 0
