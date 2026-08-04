"""CarSoul OS Virtual Vehicle Simulator.

Synthesises realistic vehicle telemetry data via a time-compression
engine. A single ``run(days=365)`` call produces a full year of daily
TelemetryFrame snapshots in seconds.

Public API
----------
::

    from simulator import create_virtual_vehicle

    v = create_virtual_vehicle("family_ev", seed=42)
    frames = v.run(days=365)

Sub-modules
-----------
  - ``profiles``   — vehicle profiles (degradation curves, sensor baselines)
  - ``scenarios``  — scenario orchestration (charging, anomalies, road mix)
  - ``virtual_vehicle`` — the time-compression engine
"""
from simulator.virtual_vehicle import VirtualVehicle, create_virtual_vehicle
from simulator.profiles import VehicleProfile, get_profile, PROFILES
from simulator.scenarios import (
    AnomalyType,
    ScenarioConfig,
    AnomalyInjection,
    ChargingHabit,
    RoadMix,
    normal_lifecycle,
    aggressive_lifecycle,
    cooling_fault_scenario,
)

__all__ = [
    "VirtualVehicle",
    "create_virtual_vehicle",
    "VehicleProfile",
    "get_profile",
    "PROFILES",
    "AnomalyType",
    "ScenarioConfig",
    "AnomalyInjection",
    "ChargingHabit",
    "RoadMix",
    "normal_lifecycle",
    "aggressive_lifecycle",
    "cooling_fault_scenario",
]
