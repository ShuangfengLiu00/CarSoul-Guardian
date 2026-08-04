"""CarSoul OS Digital Twin — Component Model.

The component model defines **state-machine twins** for each major
vehicle subsystem.  Each twin ingests TelemetryFrame data from the
simulator and evolves its state (normal → degrading → warning → critical),
producing explainable health results.

The VehicleTwin aggregates all component twins and computes an
explainable soul-score where every point deducted is traceable to a
specific component and metric.

Public API
----------
::

    from digital_twin.component_model import (
        VehicleTwin,
        BatteryTwin,
        MotorTwin,
        ChassisTwin,
        create_vehicle_twin_from_simulator,
    )

    # From simulator output:
    from simulator import create_virtual_vehicle
    frames = create_virtual_vehicle("family_ev").run(days=365)
    twin = create_vehicle_twin_from_simulator(frames)
    score = twin.soul_score()
    print(f"Soul Score: {score.score} — {score.grade}")
    for d in score.deductions:
        print(f"  -{d.points} pts: {d.reason}")
"""
from digital_twin.component_model.base import (
    ComponentHealthResult,
    ComponentTwin,
    HealthDeduction,
    SoulScoreResult,
    StateTransition,
)
from digital_twin.component_model.battery_twin import BatteryTwin
from digital_twin.component_model.chassis_twin import ChassisTwin
from digital_twin.component_model.motor_twin import MotorTwin
from digital_twin.component_model.vehicle_twin import (
    VehicleTwin,
    create_vehicle_twin_from_simulator,
)

__all__ = [
    # Twins
    "VehicleTwin",
    "BatteryTwin",
    "MotorTwin",
    "ChassisTwin",
    # Base types
    "ComponentTwin",
    "ComponentHealthResult",
    "HealthDeduction",
    "SoulScoreResult",
    "StateTransition",
    # Factory
    "create_vehicle_twin_from_simulator",
]
