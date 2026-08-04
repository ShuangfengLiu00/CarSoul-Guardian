"""Tests for the CarSoul OS Vehicle Schema (carsoul-schema).

Verifies that:
  - All models accept valid data and reject invalid data
  - JSON round-trip (serialize → deserialize) preserves data
  - JSON Schema export works and includes all models
  - Semver versioning and compatibility check work
  - The spec-document scenarios (third-party constructing data) pass
"""
import json
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from vehicle_schema import (
    SCHEMA_VERSION,
    BatteryState,
    ChassisState,
    DrivingProfile,
    ImpactRef,
    LifecycleEvent,
    MotorState,
    TelemetryFrame,
    VehicleIdentity,
    is_compatible,
)
from vehicle_schema.export import export_all_schemas, export_model_schema


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #
@pytest.fixture
def ev_identity():
    return VehicleIdentity(
        vin="LSJW32V8X1S000001",
        brand="Tesla",
        model="Model Y",
        year=2025,
        fuel_type="electric",
        battery_capacity=75.0,
    )


@pytest.fixture
def ice_identity():
    return VehicleIdentity(
        vin="WBA12345678AB1234",
        brand="BMW",
        model="330i",
        year=2024,
        fuel_type="gasoline",
    )


@pytest.fixture
def battery_state():
    return BatteryState(
        soh=98.5,
        temperature=28.0,
        charge_cycles=50,
        fast_charge_ratio=0.3,
        soc=72.0,
    )


@pytest.fixture
def motor_state():
    return MotorState(efficiency=0.95, wear=0.05, temperature=45.0)


@pytest.fixture
def chassis_state():
    return ChassisState(
        brake_wear=0.15,
        tire_wear=0.10,
        suspension_health=95.0,
        tire_pressure=2.4,
    )


@pytest.fixture
def driving_profile():
    return DrivingProfile(
        style="balanced",
        safety_score=88.0,
        eco_score=82.0,
        harsh_event_count=2,
        avg_speed=45.0,
    )


@pytest.fixture
def telemetry_frame(ev_identity, battery_state, motor_state, chassis_state, driving_profile):
    return TelemetryFrame(
        ts=datetime(2025, 8, 3, 10, 0, 0, tzinfo=timezone.utc),
        vin=ev_identity.vin,
        battery=battery_state,
        motor=motor_state,
        chassis=chassis_state,
        driving=driving_profile,
        mileage=5000,
        ambient_temp=25.0,
    )


# ------------------------------------------------------------------ #
#  VehicleIdentity
# ------------------------------------------------------------------ #
class TestVehicleIdentity:
    def test_ev_requires_battery(self):
        with pytest.raises(ValidationError, match="battery_capacity"):
            VehicleIdentity(
                vin="LSJW32V8X1S000001",
                brand="Tesla",
                model="Model Y",
                year=2025,
                fuel_type="electric",
            )

    def test_ice_battery_optional(self, ice_identity):
        assert ice_identity.battery_capacity is None

    def test_vin_too_short(self):
        with pytest.raises(ValidationError):
            VehicleIdentity(
                vin="SHORT",
                brand="Tesla",
                model="Model Y",
                year=2025,
                fuel_type="gasoline",
            )

    def test_invalid_fuel_type(self):
        with pytest.raises(ValidationError):
            VehicleIdentity(
                vin="LSJW32V8X1S000001",
                brand="Tesla",
                model="Model Y",
                year=2025,
                fuel_type="nuclear",
            )


# ------------------------------------------------------------------ #
#  BatteryState
# ------------------------------------------------------------------ #
class TestBatteryState:
    def test_valid_battery(self, battery_state):
        assert battery_state.soh == 98.5
        assert battery_state.status == "normal"

    def test_soh_out_of_range(self):
        with pytest.raises(ValidationError):
            BatteryState(soh=150, temperature=28, charge_cycles=50, fast_charge_ratio=0.3)

    def test_fast_charge_ratio_out_of_range(self):
        with pytest.raises(ValidationError):
            BatteryState(soh=90, temperature=28, charge_cycles=50, fast_charge_ratio=1.5)

    def test_negative_cycles(self):
        with pytest.raises(ValidationError):
            BatteryState(soh=90, temperature=28, charge_cycles=-1, fast_charge_ratio=0.3)


# ------------------------------------------------------------------ #
#  TelemetryFrame
# ------------------------------------------------------------------ #
class TestTelemetryFrame:
    def test_valid_frame(self, telemetry_frame):
        assert telemetry_frame.vin == "LSJW32V8X1S000001"
        assert telemetry_frame.battery is not None
        assert telemetry_frame.mileage == 5000

    def test_ice_frame_no_battery(self, ice_identity, motor_state, chassis_state, driving_profile):
        """ICE vehicles can omit battery state."""
        frame = TelemetryFrame(
            ts=datetime(2025, 8, 3, 10, 0, 0, tzinfo=timezone.utc),
            vin=ice_identity.vin,
            battery=None,
            motor=motor_state,
            chassis=chassis_state,
            driving=driving_profile,
            mileage=10000,
        )
        assert frame.battery is None

    def test_negative_mileage_rejected(self, ev_identity, motor_state, chassis_state, driving_profile):
        with pytest.raises(ValidationError):
            TelemetryFrame(
                ts=datetime(2025, 8, 3, 10, 0, 0, tzinfo=timezone.utc),
                vin=ev_identity.vin,
                motor=motor_state,
                chassis=chassis_state,
                driving=driving_profile,
                mileage=-100,
            )

    def test_json_roundtrip(self, telemetry_frame):
        """Serialize → deserialize preserves all data."""
        json_str = telemetry_frame.model_dump_json()
        restored = TelemetryFrame.model_validate_json(json_str)
        assert restored.vin == telemetry_frame.vin
        assert restored.battery.soh == telemetry_frame.battery.soh
        assert restored.mileage == telemetry_frame.mileage


# ------------------------------------------------------------------ #
#  LifecycleEvent + ImpactRef
# ------------------------------------------------------------------ #
class TestLifecycleEvent:
    def test_event_with_impact(self):
        event = LifecycleEvent(
            event_type="fault",
            date=date(2025, 7, 15),
            mileage=30000,
            title="电池温度异常",
            severity="major",
            impact=ImpactRef(target="battery_stress", delta=0.3, confidence=0.9),
        )
        assert event.impact.target == "battery_stress"
        assert event.impact.delta == 0.3

    def test_event_without_impact(self):
        event = LifecycleEvent(
            event_type="maintenance",
            date=date(2025, 6, 1),
            mileage=20000,
            title="常规保养",
        )
        assert event.impact is None

    def test_invalid_severity(self):
        with pytest.raises(ValidationError):
            LifecycleEvent(
                event_type="accident",
                date=date(2025, 1, 1),
                mileage=10000,
                title="测试",
                severity="catastrophic",
            )


# ------------------------------------------------------------------ #
#  JSON Schema export
# ------------------------------------------------------------------ #
class TestSchemaExport:
    def test_export_single_model(self):
        schema = export_model_schema("VehicleIdentity")
        assert schema["type"] == "object"
        assert "vin" in schema["properties"]

    def test_export_all_models(self):
        bundle = export_all_schemas()
        assert bundle["version"] == SCHEMA_VERSION
        assert "$defs" in bundle
        expected = {
            "VehicleIdentity", "BatteryState", "MotorState", "ChassisState",
            "DrivingProfile", "ImpactRef", "LifecycleEvent", "TelemetryFrame",
        }
        assert expected.issubset(bundle["$defs"].keys())

    def test_exported_schema_is_json_serialisable(self):
        bundle = export_all_schemas()
        json_str = json.dumps(bundle, ensure_ascii=False)
        restored = json.loads(json_str)
        assert restored["version"] == SCHEMA_VERSION


# ------------------------------------------------------------------ #
#  Versioning
# ------------------------------------------------------------------ #
class TestVersioning:
    def test_version_format(self):
        parts = SCHEMA_VERSION.split(".")
        assert len(parts) == 3
        for p in parts:
            assert p.isdigit()

    def test_compatible_same_major(self):
        assert is_compatible("1.0.0") is True
        assert is_compatible("1.5.2") is True

    def test_incompatible_different_major(self):
        assert is_compatible("2.0.0") is False
        assert is_compatible("0.9.0") is False

    def test_invalid_version(self):
        assert is_compatible("invalid") is False


# ------------------------------------------------------------------ #
#  Third-party construction scenario (spec-doc acceptance)
# ------------------------------------------------------------------ #
class TestThirdPartyConstruction:
    """Simulate a third party building valid data from the spec doc alone."""

    def test_construct_full_telemetry_from_json(self):
        """A third party reads schema-spec.md and constructs a valid frame."""
        raw_json = {
            "ts": "2025-08-03T10:00:00Z",
            "vin": "LSJW32V8X1S000001",
            "battery": {
                "soh": 95.0,
                "temperature": 30.0,
                "charge_cycles": 120,
                "fast_charge_ratio": 0.4,
                "soc": 65.0,
                "status": "normal",
            },
            "motor": {
                "efficiency": 0.92,
                "wear": 0.1,
                "temperature": 50.0,
                "status": "normal",
            },
            "chassis": {
                "brake_wear": 0.2,
                "tire_wear": 0.15,
                "suspension_health": 90.0,
                "tire_pressure": 2.3,
                "status": "normal",
            },
            "driving": {
                "style": "eco",
                "safety_score": 92.0,
                "eco_score": 88.0,
                "harsh_event_count": 1,
                "avg_speed": 40.0,
            },
            "mileage": 15000,
            "ambient_temp": 22.0,
        }
        frame = TelemetryFrame.model_validate(raw_json)
        assert frame.battery.soh == 95.0
        assert frame.driving.style == "eco"
        assert frame.chassis.brake_wear == 0.2

    def test_construct_invalid_data_rejected(self):
        """Out-of-range values are rejected by validation."""
        raw_json = {
            "ts": "2025-08-03T10:00:00Z",
            "vin": "LSJW32V8X1S000001",
            "motor": {"efficiency": 1.5, "wear": 0.1},  # efficiency > 1
            "chassis": {"brake_wear": 0.2, "tire_wear": 0.15, "suspension_health": 90.0},
            "driving": {"style": "balanced", "safety_score": 80.0, "eco_score": 75.0},
            "mileage": 15000,
        }
        with pytest.raises(ValidationError):
            TelemetryFrame.model_validate(raw_json)
