"""CarSoul OS Vehicle Schema (``carsoul-schema``).

The public data standard for the CarSoul OS vehicle protocol layer.
Independent of ORM and database — pure Pydantic v2 models that define
the contract between simulator, digital twin, and agent runtime.

Quickstart
----------
::

    from vehicle_schema import (
        VehicleIdentity, TelemetryFrame, BatteryState, SCHEMA_VERSION,
    )

    identity = VehicleIdentity(
        vin="LSJW32V8X1S000001",
        brand="Tesla",
        model="Model Y",
        year=2025,
        fuel_type="electric",
        battery_capacity=75.0,
    )

    frame = TelemetryFrame(
        ts="2025-08-03T10:00:00Z",
        vin=identity.vin,
        battery=BatteryState(soh=98.5, temperature=28.0, charge_cycles=50, fast_charge_ratio=0.3),
        motor=...,
        chassis=...,
        driving=...,
        mileage=5000,
    )

Versioning
----------
Check ``SCHEMA_VERSION`` for compatibility. See ``version.py``.
"""
from __future__ import annotations

from vehicle_schema.models import (
    BatteryState,
    ChassisState,
    ComponentStatus,
    DrivingProfile,
    DrivingStyle,
    EventType,
    FuelType,
    ImpactRef,
    LifecycleEvent,
    MotorState,
    TelemetryFrame,
    VehicleIdentity,
)
from vehicle_schema.version import (
    SCHEMA_VERSION,
    SCHEMA_VERSION_TUPLE,
    is_compatible,
)

__version__ = SCHEMA_VERSION

__all__ = [
    # Models
    "VehicleIdentity",
    "BatteryState",
    "MotorState",
    "ChassisState",
    "DrivingProfile",
    "ImpactRef",
    "LifecycleEvent",
    "TelemetryFrame",
    # Types
    "FuelType",
    "DrivingStyle",
    "ComponentStatus",
    "EventType",
    # Versioning
    "SCHEMA_VERSION",
    "SCHEMA_VERSION_TUPLE",
    "is_compatible",
]
