"""CarSoul OS Vehicle Schema — Pydantic v2 data standard.

This module defines the public data contracts that flow between the
simulator, digital twin, agent runtime, and external consumers.  Every
model is serialisable to / from JSON and carries field-level
constraints (units, ranges, enumerations) so that any third party can
construct valid data by following this schema alone.

Model map
---------
  VehicleIdentity   — who the vehicle is (VIN, brand, powertrain)
  BatteryState      — battery health snapshot (EV / hybrid only)
  MotorState        — motor / engine efficiency and wear
  ChassisState      — brake / tyre / suspension health
  DrivingProfile    — driving style and behaviour scores
  ImpactRef         — reference to a memory-engine impact entry
  LifecycleEvent    — a point on the vehicle's life timeline
  TelemetryFrame    — the atomic emission unit of the simulator

All field-level constraints are documented in ``docs/schema-spec.md``.
"""
from datetime import date as Date, datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ------------------------------------------------------------------ #
#  Enums / literals
# ------------------------------------------------------------------ #
FuelType = Literal["gasoline", "diesel", "hybrid", "plug_in_hybrid", "electric"]
DrivingStyle = Literal["eco", "balanced", "aggressive", "sporty"]
ComponentStatus = Literal["normal", "degrading", "warning", "critical"]


class EventType(str, Enum):
    """Vehicle lifecycle event types."""

    PURCHASE = "purchase"
    TRANSFER = "transfer"
    ACCIDENT = "accident"
    REPAIR = "repair"
    MAINTENANCE = "maintenance"
    INSPECTION = "inspection"
    INSURANCE = "insurance"
    REGISTRATION = "registration"
    FAULT = "fault"
    CUSTOM = "custom"


# ------------------------------------------------------------------ #
#  1. VehicleIdentity
# ------------------------------------------------------------------ #
class VehicleIdentity(BaseModel):
    """Immutable identity of a single vehicle.

    This is the root reference for every other model — all telemetry,
    lifecycle events, and memory entries are scoped to a VIN.
    """

    vin: str = Field(
        ...,
        min_length=11,
        max_length=17,
        description="Vehicle Identification Number (ISO 3779). 11-17 chars.",
    )
    brand: str = Field(..., min_length=1, max_length=64, description="Manufacturer brand.")
    model: str = Field(..., min_length=1, max_length=64, description="Model name.")
    year: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="Model year (e.g. 2025).",
    )
    fuel_type: FuelType = Field(..., description="Primary energy type.")
    battery_capacity: Optional[float] = Field(
        None,
        ge=0,
        description="Battery pack capacity in kWh. Required for EV/hybrid; "
        "None for pure ICE vehicles.",
    )
    engine_type: Optional[str] = Field(
        None, max_length=64, description="Engine / motor designation."
    )
    displacement: Optional[float] = Field(
        None, ge=0, description="Engine displacement in litres (L). ICE only."
    )

    @model_validator(mode="after")
    def _validate_battery_for_ev(self):
        """EV / hybrid vehicles must declare a battery capacity."""
        if self.fuel_type in ("electric", "hybrid", "plug_in_hybrid"):
            if self.battery_capacity is None:
                raise ValueError(
                    f"battery_capacity is required for fuel_type '{self.fuel_type}'"
                )
        return self


# ------------------------------------------------------------------ #
#  2. BatteryState
# ------------------------------------------------------------------ #
class BatteryState(BaseModel):
    """Battery health snapshot.

    Emitted by the simulator and consumed by the digital-twin
    BatteryTwin state machine.  ``soh`` (state-of-health) is the
    primary longevity indicator: 100 % = new, < 80 % = degraded.
    """

    soh: float = Field(
        ...,
        ge=0,
        le=100,
        description="State of Health (%). 100 = new battery.",
    )
    temperature: float = Field(
        ...,
        ge=-40,
        le=120,
        description="Battery pack temperature (°C).",
    )
    charge_cycles: int = Field(
        ...,
        ge=0,
        description="Total charge cycles completed.",
    )
    fast_charge_ratio: float = Field(
        ...,
        ge=0,
        le=1,
        description="Fraction of charging sessions that were fast-charge "
        "(0.0 = all slow, 1.0 = all fast).",
    )
    soc: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="State of Charge (%) at the time of this reading.",
    )
    status: ComponentStatus = Field(
        "normal",
        description="Derived component-health status.",
    )


# ------------------------------------------------------------------ #
#  3. MotorState
# ------------------------------------------------------------------ #
class MotorState(BaseModel):
    """Motor / engine efficiency and wear snapshot.

    For EVs this reflects the electric motor; for ICE vehicles it
    reflects the combustion engine.  ``wear`` is a 0-1 value where
    0 = pristine and 1 = end-of-life.
    """

    efficiency: float = Field(
        ...,
        ge=0,
        le=1,
        description="Current efficiency ratio (0-1). 1.0 = design efficiency.",
    )
    wear: float = Field(
        ...,
        ge=0,
        le=1,
        description="Wear level (0-1). 0 = pristine, 1 = end-of-life.",
    )
    temperature: Optional[float] = Field(
        None,
        ge=-40,
        le=200,
        description="Motor / engine temperature (°C).",
    )
    status: ComponentStatus = Field(
        "normal",
        description="Derived component-health status.",
    )


# ------------------------------------------------------------------ #
#  4. ChassisState
# ------------------------------------------------------------------ #
class ChassisState(BaseModel):
    """Chassis component health snapshot.

    Covers braking, tyres, and suspension — the wear-intensive
    subsystems that the chassis expert and safety agent analyse.
    """

    brake_wear: float = Field(
        ...,
        ge=0,
        le=1,
        description="Brake-pad wear (0-1). 0 = new, 1 = replace immediately.",
    )
    tire_wear: float = Field(
        ...,
        ge=0,
        le=1,
        description="Tyre-tread wear (0-1). 0 = full tread, 1 = bald.",
    )
    suspension_health: float = Field(
        ...,
        ge=0,
        le=100,
        description="Suspension health score (0-100). 100 = excellent.",
    )
    tire_pressure: Optional[float] = Field(
        None,
        ge=0,
        le=5,
        description="Average tyre pressure (bar).",
    )
    status: ComponentStatus = Field(
        "normal",
        description="Derived component-health status.",
    )


# ------------------------------------------------------------------ #
#  5. DrivingProfile
# ------------------------------------------------------------------ #
class DrivingProfile(BaseModel):
    """Driving-behaviour summary for a period.

    Aggregates a driver's style and behaviour scores.  Feeds the
    driving-behaviour expert and the energy-optimisation expert.
    """

    style: DrivingStyle = Field(
        ...,
        description="Classified driving style.",
    )
    safety_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Safety score (0-100). 100 = safest.",
    )
    eco_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Eco / energy-efficiency score (0-100). 100 = most efficient.",
    )
    harsh_event_count: int = Field(
        0,
        ge=0,
        description="Total harsh events (hard accel / brake / sharp turn) "
        "in the aggregation period.",
    )
    avg_speed: Optional[float] = Field(
        None,
        ge=0,
        description="Average speed (km/h) in the period.",
    )


# ------------------------------------------------------------------ #
#  6. ImpactRef + LifecycleEvent
# ------------------------------------------------------------------ #
class ImpactRef(BaseModel):
    """Reference to a memory-engine impact entry.

    When a lifecycle event (e.g. a fault) has a quantified impact on a
    vehicle component, this links the event to the memory-engine record
    so that downstream agents can trace cause → effect.
    """

    target: str = Field(
        ...,
        description="Affected component or metric (e.g. 'battery_stress').",
    )
    delta: float = Field(
        ...,
        description="Signed impact magnitude (e.g. +0.3 stress, -5 health).",
    )
    confidence: float = Field(
        0.8,
        ge=0,
        le=1,
        description="Confidence in the impact assessment (0-1).",
    )


class LifecycleEvent(BaseModel):
    """A single point on the vehicle's life timeline.

    Lifecycle events are the raw log; the memory engine (Step 4) adds
    an interpretation layer on top via ``ImpactRef``.
    """

    event_type: EventType = Field(..., description="Event category.")
    date: Date = Field(..., description="When the event occurred.")
    mileage: float = Field(
        ...,
        ge=0,
        description="Odometer reading at event time (km).",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Human-readable event title.",
    )
    description: Optional[str] = Field(
        None, description="Detailed event description."
    )
    severity: Optional[Literal["info", "minor", "moderate", "major", "critical"]] = (
        Field(None, description="Severity (for accidents / faults).")
    )
    cost: Optional[float] = Field(
        None, ge=0, description="Associated cost (CNY)."
    )
    impact: Optional[ImpactRef] = Field(
        None,
        description="Optional link to a memory-engine impact entry.",
    )


# ------------------------------------------------------------------ #
#  7. TelemetryFrame
# ------------------------------------------------------------------ #
class TelemetryFrame(BaseModel):
    """The atomic emission unit of the virtual-vehicle simulator.

    A TelemetryFrame is a complete point-in-time snapshot of a vehicle's
    subsystem states, produced by the simulator's time-compression
    engine.  Each frame flows: Simulator → Digital Twin → Agent Runtime.

    The ``vin`` links the frame back to a VehicleIdentity; the timestamp
    allows the memory engine and timeline demo to replay history.
    """

    ts: datetime = Field(
        ...,
        description="Frame timestamp (UTC). Marks when this snapshot was "
        "produced by the simulator.",
    )
    vin: str = Field(
        ...,
        min_length=11,
        max_length=17,
        description="Vehicle Identification Number this frame belongs to.",
    )
    battery: Optional[BatteryState] = Field(
        None,
        description="Battery state (EV / hybrid only; None for pure ICE).",
    )
    motor: MotorState = Field(
        ...,
        description="Motor / engine state.",
    )
    chassis: ChassisState = Field(
        ...,
        description="Chassis state.",
    )
    driving: DrivingProfile = Field(
        ...,
        description="Driving profile for the period ending at this frame.",
    )
    mileage: float = Field(
        ...,
        ge=0,
        description="Odometer reading at frame time (km).",
    )
    ambient_temp: Optional[float] = Field(
        None,
        ge=-50,
        le=60,
        description="Ambient (environment) temperature (°C).",
    )

    @field_validator("battery")
    @classmethod
    def _validate_battery_present(cls, v, info):
        """Warn-level check: EVs should carry battery state."""
        # We keep this lenient (no raise) because the VIN alone doesn't
        # tell us the fuel type; the simulator is responsible for
        # populating battery for EVs.
        return v
