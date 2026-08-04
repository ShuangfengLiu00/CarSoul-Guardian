"""Tests for the CarSoul OS Virtual Vehicle Simulator.

Verifies that:
  - ``create_virtual_vehicle('family_ev').run(days=365)`` produces 365
    schema-compliant TelemetryFrame objects
  - Same profile + seed + scenario always produces identical output
  - Anomaly injection scenarios cause detectable deviations (temperature
    spikes, accelerated SoH degradation)
  - All three built-in profiles produce valid telemetry
  - Streaming mode (``run_iter``) yields the same data as ``run``
  - TelemetryFrame JSON round-trip works for simulator output
  - Mileage monotonically increases; SoH monotonically decreases
  - Scores stay within [0, 100] and wear stays within [0, 1]
"""
import json
from datetime import datetime, timezone

import pytest

from vehicle_schema import TelemetryFrame

from simulator import (
    PROFILES,
    AnomalyInjection,
    AnomalyType,
    ChargingHabit,
    RoadMix,
    ScenarioConfig,
    VirtualVehicle,
    aggressive_lifecycle,
    cooling_fault_scenario,
    create_virtual_vehicle,
    get_profile,
    normal_lifecycle,
)
from simulator.profiles import FAMILY_EV, HYBRID, PERFORMANCE_EV
from simulator.scenarios import seasonal_ambient_temp


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #
@pytest.fixture
def family_vehicle():
    return create_virtual_vehicle("family_ev", seed=42)


@pytest.fixture
def performance_vehicle():
    return create_virtual_vehicle("performance_ev", seed=99)


@pytest.fixture
def hybrid_vehicle():
    return create_virtual_vehicle("hybrid", seed=7)


# ------------------------------------------------------------------ #
#  1. Basic factory & profile tests
# ------------------------------------------------------------------ #
class TestFactoryAndProfiles:
    def test_create_virtual_vehicle_returns_instance(self, family_vehicle):
        assert isinstance(family_vehicle, VirtualVehicle)

    def test_factory_sets_seed(self, family_vehicle):
        assert family_vehicle.seed == 42

    def test_factory_generates_vin(self, family_vehicle):
        assert len(family_vehicle.vin) >= 11
        assert len(family_vehicle.vin) <= 17

    def test_factory_custom_vin(self):
        v = create_virtual_vehicle("family_ev", seed=42, vin="LSJW32V8X1S000042")
        assert v.vin == "LSJW32V8X1S000042"

    def test_unknown_profile_raises(self):
        with pytest.raises(KeyError, match="Unknown vehicle profile"):
            create_virtual_vehicle("nonexistent_profile")

    def test_get_profile_returns_correct(self):
        p = get_profile("family_ev")
        assert p.name == "family_ev"
        assert p.brand == "BYD"

    def test_all_profiles_in_registry(self):
        assert set(PROFILES.keys()) == {"performance_ev", "family_ev", "hybrid"}

    def test_profiles_are_frozen(self):
        """VehicleProfile is a frozen dataclass."""
        with pytest.raises(AttributeError):
            FAMILY_EV.brand = "Wrong"

    def test_profiles_have_required_fields(self):
        for name, profile in PROFILES.items():
            assert profile.name == name
            assert len(profile.brand) > 0
            assert len(profile.model) > 0
            assert 1900 <= profile.year <= 2100
            assert profile.fuel_type in ("gasoline", "diesel", "hybrid",
                                         "plug_in_hybrid", "electric")
            assert profile.motor_efficiency_new > 0
            assert profile.motor_efficiency_new <= 1.0

    def test_ev_profiles_have_battery(self):
        assert FAMILY_EV.battery_capacity is not None
        assert PERFORMANCE_EV.battery_capacity is not None
        assert HYBRID.battery_capacity is not None

    def test_degradation_curves_positive(self):
        for profile in PROFILES.values():
            deg = profile.degradation
            assert deg.battery_soh_per_10k > 0
            assert deg.motor_wear_per_10k > 0
            assert deg.brake_wear_per_10k > 0
            assert deg.tire_wear_per_10k > 0
            assert deg.fast_charge_stress >= 1.0
            assert deg.aggressive_multiplier >= 1.0


# ------------------------------------------------------------------ #
#  2. 365-day compliant telemetry (acceptance test)
# ------------------------------------------------------------------ #
class TestYearLongCompliance:
    """The acceptance test: create_virtual_vehicle('family_ev').run(days=365)."""

    def test_produces_365_frames(self, family_vehicle):
        frames = family_vehicle.run(days=365)
        assert len(frames) == 365

    def test_all_frames_are_telemetry_frames(self, family_vehicle):
        frames = family_vehicle.run(days=365)
        for f in frames:
            assert isinstance(f, TelemetryFrame)

    def test_all_frames_schema_compliant(self, family_vehicle):
        """Every frame must pass Pydantic validation (already done by the model,
        but we also verify JSON round-trip to be thorough)."""
        frames = family_vehicle.run(days=365)
        for f in frames:
            json_str = f.model_dump_json()
            restored = TelemetryFrame.model_validate_json(json_str)
            assert restored.vin == f.vin
            assert restored.mileage == f.mileage

    def test_frames_are_chronologically_ordered(self, family_vehicle):
        frames = family_vehicle.run(days=365)
        for i in range(1, len(frames)):
            assert frames[i].ts > frames[i - 1].ts

    def test_mileage_monotonically_increasing(self, family_vehicle):
        frames = family_vehicle.run(days=365)
        for i in range(1, len(frames)):
            assert frames[i].mileage >= frames[i - 1].mileage

    def test_soh_monotonically_decreasing(self, family_vehicle):
        frames = family_vehicle.run(days=365)
        for i in range(1, len(frames)):
            if frames[i].battery and frames[i - 1].battery:
                assert frames[i].battery.soh <= frames[i - 1].battery.soh + 0.01

    def test_soh_within_valid_range(self, family_vehicle):
        frames = family_vehicle.run(days=365)
        for f in frames:
            if f.battery:
                assert 0 <= f.battery.soh <= 100

    def test_wear_within_valid_range(self, family_vehicle):
        frames = family_vehicle.run(days=365)
        for f in frames:
            assert 0 <= f.motor.wear <= 1
            assert 0 <= f.chassis.brake_wear <= 1
            assert 0 <= f.chassis.tire_wear <= 1
            assert 0 <= f.chassis.suspension_health <= 100

    def test_scores_within_valid_range(self, family_vehicle):
        frames = family_vehicle.run(days=365)
        for f in frames:
            assert 0 <= f.driving.safety_score <= 100
            assert 0 <= f.driving.eco_score <= 100
            assert f.driving.harsh_event_count >= 0

    def test_temperatures_within_valid_range(self, family_vehicle):
        frames = family_vehicle.run(days=365)
        for f in frames:
            if f.battery:
                assert -40 <= f.battery.temperature <= 120
            if f.motor.temperature is not None:
                assert -40 <= f.motor.temperature <= 200
            if f.ambient_temp is not None:
                assert -50 <= f.ambient_temp <= 60

    def test_ev_frames_have_battery_state(self, family_vehicle):
        """EV profile must produce battery state in every frame."""
        frames = family_vehicle.run(days=365)
        for f in frames:
            assert f.battery is not None
            assert f.battery.soh > 0

    def test_vin_consistent_across_frames(self, family_vehicle):
        frames = family_vehicle.run(days=365)
        vins = {f.vin for f in frames}
        assert len(vins) == 1
        assert family_vehicle.vin in vins

    def test_final_mileage_reasonable(self, family_vehicle):
        """After 365 days, mileage should be in a realistic range."""
        frames = family_vehicle.run(days=365)
        final = frames[-1].mileage
        # Family EV: ~35 km/day average → ~5000–25000 km/year
        assert 1000 < final < 50000

    def test_soh_degradation_over_year(self, family_vehicle):
        """SoH should decrease but remain high after one year of normal use."""
        frames = family_vehicle.run(days=365)
        initial = frames[0].battery.soh
        final = frames[-1].battery.soh
        assert final < initial  # degradation occurred
        assert final > 80.0    # still healthy after 1 year


# ------------------------------------------------------------------ #
#  3. Seed reproducibility
# ------------------------------------------------------------------ #
class TestSeedReproducibility:
    def test_same_seed_same_output(self):
        v1 = create_virtual_vehicle("family_ev", seed=42)
        v2 = create_virtual_vehicle("family_ev", seed=42)
        f1 = v1.run(days=30)
        f2 = v2.run(days=30)
        assert len(f1) == len(f2)
        for a, b in zip(f1, f2):
            assert a.ts == b.ts
            assert a.mileage == b.mileage
            assert a.battery.soh == b.battery.soh

    def test_different_seed_different_output(self):
        v1 = create_virtual_vehicle("family_ev", seed=42)
        v2 = create_virtual_vehicle("family_ev", seed=999)
        f1 = v1.run(days=30)
        f2 = v2.run(days=30)
        # At least some frames should differ.
        diffs = sum(1 for a, b in zip(f1, f2) if a.mileage != b.mileage)
        assert diffs > 0

    def test_same_seed_same_vin(self):
        v1 = create_virtual_vehicle("family_ev", seed=42)
        v2 = create_virtual_vehicle("family_ev", seed=42)
        assert v1.vin == v2.vin

    def test_different_seed_different_vin(self):
        v1 = create_virtual_vehicle("family_ev", seed=42)
        v2 = create_virtual_vehicle("family_ev", seed=100)
        assert v1.vin != v2.vin

    def test_json_output_identical(self):
        """Full JSON serialisation must be byte-identical for same seed."""
        v1 = create_virtual_vehicle("performance_ev", seed=77)
        v2 = create_virtual_vehicle("performance_ev", seed=77)
        f1 = v1.run(days=10)
        f2 = v2.run(days=10)
        j1 = json.dumps([f.model_dump() for f in f1], default=str, sort_keys=True)
        j2 = json.dumps([f.model_dump() for f in f2], default=str, sort_keys=True)
        assert j1 == j2

    def test_scenario_reproducibility(self):
        """Same scenario + seed produces identical output."""
        scenario = cooling_fault_scenario()
        v1 = create_virtual_vehicle("family_ev", seed=42)
        v2 = create_virtual_vehicle("family_ev", seed=42)
        f1 = v1.run(days=600, scenario=scenario)
        f2 = v2.run(days=600, scenario=scenario)
        for a, b in zip(f1, f2):
            assert a.battery.soh == b.battery.soh
            assert a.battery.temperature == b.battery.temperature


# ------------------------------------------------------------------ #
#  4. Anomaly injection
# ------------------------------------------------------------------ #
class TestAnomalyInjection:
    def test_cooling_failure_raises_temperature(self):
        """The cooling_fault_scenario should cause battery temp to spike."""
        scenario = cooling_fault_scenario()
        v = create_virtual_vehicle("family_ev", seed=42)
        frames = v.run(days=600, scenario=scenario)

        # Before the anomaly (day < 450), temps should be normal.
        normal_temps = [f.battery.temperature for f in frames[:400]
                        if f.battery]
        anomaly_temps = [f.battery.temperature for f in frames[500:]
                         if f.battery]

        avg_normal = sum(normal_temps) / len(normal_temps)
        avg_anomaly = sum(anomaly_temps) / len(anomaly_temps)

        assert avg_anomaly > avg_normal + 5.0  # significant temperature rise

    def test_cell_imbalance_accelerates_soh_loss(self):
        """CELL_IMBALANCE anomaly should accelerate battery SoH degradation."""
        # Normal scenario
        v_normal = create_virtual_vehicle("family_ev", seed=42)
        normal_frames = v_normal.run(days=600, scenario=normal_lifecycle())

        # Anomaly scenario
        anomaly_scenario = ScenarioConfig(
            anomalies=[
                AnomalyInjection(
                    anomaly_type=AnomalyType.CELL_IMBALANCE,
                    start_day=100,
                    ramp_days=30,
                    severity=1.0,
                ),
            ],
        )
        v_anomaly = create_virtual_vehicle("family_ev", seed=42)
        anomaly_frames = v_anomaly.run(days=600, scenario=anomaly_scenario)

        normal_final_soh = normal_frames[-1].battery.soh
        anomaly_final_soh = anomaly_frames[-1].battery.soh

        # Anomaly scenario should have lower SoH.
        assert anomaly_final_soh < normal_final_soh - 1.0

    def test_brake_fault_accelerates_wear(self):
        """BRAKE_SYSTEM_FAULT should accelerate brake pad wear."""
        anomaly_scenario = ScenarioConfig(
            anomalies=[
                AnomalyInjection(
                    anomaly_type=AnomalyType.BRAKE_SYSTEM_FAULT,
                    start_day=50,
                    ramp_days=30,
                    severity=1.0,
                ),
            ],
        )
        v_anomaly = create_virtual_vehicle("family_ev", seed=42)
        v_normal = create_virtual_vehicle("family_ev", seed=42)

        anomaly_frames = v_anomaly.run(days=200, scenario=anomaly_scenario)
        normal_frames = v_normal.run(days=200, scenario=normal_lifecycle())

        assert (anomaly_frames[-1].chassis.brake_wear
                > normal_frames[-1].chassis.brake_wear)

    def test_motor_overheat_raises_temperature(self):
        """MOTOR_OVERHEAT should raise motor temperature."""
        anomaly_scenario = ScenarioConfig(
            anomalies=[
                AnomalyInjection(
                    anomaly_type=AnomalyType.MOTOR_OVERHEAT,
                    start_day=30,
                    ramp_days=20,
                    severity=1.0,
                ),
            ],
        )
        v = create_virtual_vehicle("performance_ev", seed=42)
        frames = v.run(days=100, scenario=anomaly_scenario)

        normal_motor_temps = [f.motor.temperature for f in frames[:30]]
        anomaly_motor_temps = [f.motor.temperature for f in frames[60:]]

        avg_normal = sum(normal_motor_temps) / len(normal_motor_temps)
        avg_anomaly = sum(anomaly_motor_temps) / len(anomaly_motor_temps)

        assert avg_anomaly > avg_normal + 10.0

    def test_anomaly_intensity_ramp(self):
        """Anomaly intensity ramps linearly from 0 to severity."""
        inj = AnomalyInjection(
            anomaly_type=AnomalyType.COOLING_FAILURE,
            start_day=100,
            ramp_days=50,
            severity=0.8,
        )
        assert inj.intensity(99) == 0.0   # before start
        assert inj.intensity(100) == 0.0  # at start (0 days into)
        assert 0 < inj.intensity(125) < 0.8  # mid-ramp
        assert abs(inj.intensity(150) - 0.8) < 0.01  # full severity
        assert abs(inj.intensity(300) - 0.8) < 0.01  # persists

    def test_anomaly_with_end_day(self):
        """Anomaly with end_day stops after the end."""
        inj = AnomalyInjection(
            anomaly_type=AnomalyType.CELL_IMBALANCE,
            start_day=100,
            ramp_days=20,
            end_day=200,
            severity=1.0,
        )
        assert inj.is_active(99) is False
        assert inj.is_active(100) is True
        assert inj.is_active(199) is True
        assert inj.is_active(200) is False

    def test_normal_scenario_no_anomalies(self):
        """Normal lifecycle should have no active anomalies."""
        scenario = normal_lifecycle()
        assert len(scenario.anomalies) == 0
        assert scenario.anomaly_intensity(AnomalyType.COOLING_FAILURE, 100) == 0.0


# ------------------------------------------------------------------ #
#  5. Scenario configuration
# ------------------------------------------------------------------ #
class TestScenarioConfig:
    def test_charging_habit_ratio_clamped(self):
        ch = ChargingHabit(base_ratio=0.9, drift_per_year=0.5)
        assert ch.ratio_at(0) == 0.9
        assert ch.ratio_at(1) == 1.0  # clamped to 1.0
        assert ch.ratio_at(10) == 1.0

    def test_charging_habit_negative_clamped(self):
        ch = ChargingHabit(base_ratio=0.1, drift_per_year=-0.5)
        assert ch.ratio_at(1) == 0.0  # clamped to 0.0

    def test_road_mix_samples_valid_types(self):
        import random
        rng = random.Random(42)
        rm = RoadMix()
        samples = {rm.sample(rng) for _ in range(100)}
        assert samples.issubset({"urban", "highway", "suburban",
                                 "mountain", "rural"})

    def test_aggressive_lifecycle_has_higher_fast_charge(self):
        normal = normal_lifecycle()
        aggressive = aggressive_lifecycle()
        assert aggressive.charging.ratio_at(0) > normal.charging.ratio_at(0)

    def test_scenario_anomaly_intensity_capped(self):
        """Multiple anomalies of same type are capped at 1.0."""
        scenario = ScenarioConfig(
            anomalies=[
                AnomalyInjection(AnomalyType.COOLING_FAILURE,
                                 start_day=0, ramp_days=1, severity=0.8),
                AnomalyInjection(AnomalyType.COOLING_FAILURE,
                                 start_day=0, ramp_days=1, severity=0.7),
            ],
        )
        # 0.8 + 0.7 = 1.5, should be capped at 1.0
        assert scenario.anomaly_intensity(AnomalyType.COOLING_FAILURE, 5) == 1.0

    def test_seasonal_ambient_temp(self):
        """Seasonal temperature varies by month."""
        from datetime import date
        jan = seasonal_ambient_temp(date(2025, 1, 15))
        jul = seasonal_ambient_temp(date(2025, 7, 15))
        assert jan < 15.0   # winter
        assert jul > 25.0   # summer


# ------------------------------------------------------------------ #
#  6. Streaming mode
# ------------------------------------------------------------------ #
class TestStreamingMode:
    def test_run_iter_yields_same_as_run(self, family_vehicle):
        frames_list = family_vehicle.run(days=30)
        family_vehicle2 = create_virtual_vehicle("family_ev", seed=42)
        frames_iter = list(family_vehicle2.run_iter(days=30))

        assert len(frames_list) == len(frames_iter)
        for a, b in zip(frames_list, frames_iter):
            assert a.ts == b.ts
            assert a.mileage == b.mileage
            assert a.battery.soh == b.battery.soh

    def test_run_iter_is_iterator(self, family_vehicle):
        it = family_vehicle.run_iter(days=5)
        first = next(it)
        assert isinstance(first, TelemetryFrame)
        remaining = list(it)
        assert len(remaining) == 4


# ------------------------------------------------------------------ #
#  7. All profiles produce valid data
# ------------------------------------------------------------------ #
class TestAllProfiles:
    @pytest.mark.parametrize("profile_name", ["performance_ev", "family_ev", "hybrid"])
    def test_profile_produces_valid_year(self, profile_name):
        v = create_virtual_vehicle(profile_name, seed=42)
        frames = v.run(days=365)
        assert len(frames) == 365

        # Spot-check first and last frame.
        first = frames[0]
        last = frames[-1]

        assert isinstance(first, TelemetryFrame)
        assert isinstance(last, TelemetryFrame)
        assert last.mileage > first.mileage

        # All EV/hybrid frames should have battery state.
        for f in frames:
            assert f.battery is not None

    @pytest.mark.parametrize("profile_name", ["performance_ev", "family_ev", "hybrid"])
    def test_profile_json_serialisable(self, profile_name):
        v = create_virtual_vehicle(profile_name, seed=42)
        frames = v.run(days=10)
        for f in frames:
            json_str = f.model_dump_json()
            assert len(json_str) > 10
            restored = TelemetryFrame.model_validate_json(json_str)
            assert restored.vin == f.vin


# ------------------------------------------------------------------ #
#  8. Acceptance: the exact demo command from the spec
# ------------------------------------------------------------------ #
class TestAcceptance:
    def test_demo_command(self):
        """Exact acceptance test from the upgrade plan:

        ``create_virtual_vehicle('family_ev').run(days=365)`` must produce
        compliant data.
        """
        v = create_virtual_vehicle("family_ev")
        frames = v.run(days=365)

        # 1. Exactly 365 frames.
        assert len(frames) == 365

        # 2. Every frame is a valid TelemetryFrame.
        for f in frames:
            assert isinstance(f, TelemetryFrame)
            assert f.vin is not None
            assert f.mileage >= 0
            assert f.battery is not None
            assert 0 <= f.battery.soh <= 100
            assert -40 <= f.battery.temperature <= 120
            assert 0 <= f.motor.wear <= 1
            assert 0 <= f.chassis.brake_wear <= 1
            assert 0 <= f.driving.safety_score <= 100
            assert 0 <= f.driving.eco_score <= 100

        # 3. Mileage is monotonically increasing.
        for i in range(1, len(frames)):
            assert frames[i].mileage >= frames[i - 1].mileage

        # 4. SoH degraded over the year but remains healthy.
        assert frames[-1].battery.soh < frames[0].battery.soh
        assert frames[-1].battery.soh > 80.0

        # 5. JSON round-trip works for every frame.
        for f in frames:
            restored = TelemetryFrame.model_validate_json(f.model_dump_json())
            assert restored.mileage == f.mileage

    def test_demo_cooling_fault_scenario(self):
        """The 'killer demo' scenario: cooling fault in year 2."""
        v = create_virtual_vehicle("family_ev", seed=42)
        frames = v.run(days=600, scenario=cooling_fault_scenario())

        assert len(frames) == 600

        # Year 1 should be healthy (no anomaly yet).
        year1_temps = [f.battery.temperature for f in frames[:365]]
        avg_year1 = sum(year1_temps) / len(year1_temps)

        # After anomalies kick in (~day 450+), temperatures should rise.
        year2_anomaly_temps = [f.battery.temperature for f in frames[500:]]
        avg_year2 = sum(year2_anomaly_temps) / len(year2_anomaly_temps)

        assert avg_year2 > avg_year1 + 3.0  # detectable temperature rise

        # The status should reflect the anomaly at some point.
        statuses = {f.battery.status for f in frames[500:]}
        assert "warning" in statuses or "critical" in statuses
