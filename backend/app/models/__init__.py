"""ORM models — full vehicle digital-life archive schema (TASK007 + V2).

All tables are registered on the declarative base so that
`Base.metadata.create_all()` creates them at startup.
"""
from app.models.alert import VehicleAlert
from app.models.digital_life import (
    DriverProfile,
    VehicleHealthMetrics,
    VehicleIdentity,
    VehicleLifeEvent,
    VehicleLifeState,
    VehicleMemory,
    VehiclePrediction,
    VehicleSensorStream,
    VehicleSoulScoreHistory,
)
from app.models.digital_state import VehicleDigitalState
from app.models.digital_twin import VehicleDigitalTwin
from app.models.driving_behavior import VehicleDrivingBehavior
from app.models.fault_log import VehicleFaultLog
from app.models.health_snapshot import VehicleHealthItem, VehicleHealthSnapshot
from app.models.lifecycle_event import VehicleLifecycleEvent
from app.models.maintenance import (
    VehicleMaintenanceRecord,
    VehicleMaintenanceSchedule,
)
from app.models.ownership_record import VehicleOwnershipRecord
from app.models.risk_prediction import RiskPrediction
from app.models.service_order import VehicleServiceOrder
from app.models.sensor_data import VehicleSensorData
from app.models.trip import VehicleTrip
from app.models.user import User
from app.models.vehicle import Vehicle

__all__ = [
    "User",
    "Vehicle",
    "VehicleLifecycleEvent",
    "VehicleHealthSnapshot",
    "VehicleHealthItem",
    "VehicleMaintenanceRecord",
    "VehicleMaintenanceSchedule",
    "VehicleDrivingBehavior",
    "VehicleAlert",
    "VehicleOwnershipRecord",
    "VehicleDigitalTwin",
    "RiskPrediction",
    "VehicleServiceOrder",
    # TASK007 digital-life core tables
    "VehicleSensorData",
    "VehicleTrip",
    "VehicleFaultLog",
    "VehicleDigitalState",
    # TASK007-V2 digital life engine tables
    "VehicleIdentity",
    "VehicleLifeState",
    "VehicleHealthMetrics",
    "VehicleSensorStream",
    "VehicleLifeEvent",
    "VehicleMemory",
    "DriverProfile",
    "VehiclePrediction",
    "VehicleSoulScoreHistory",
]
