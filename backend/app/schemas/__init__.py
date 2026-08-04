"""Pydantic v2 request/response schemas — full archive (TASK007)."""
from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.schemas.alert import (
    AlertCreate,
    AlertList,
    AlertOut,
    AlertUpdate,
)
from app.schemas.digital_state import (
    DigitalStateCreate,
    DigitalStateOut,
    DigitalStateUpdate,
)
from app.schemas.digital_twin import (
    DigitalTwinCreate,
    DigitalTwinOut,
    DigitalTwinUpdate,
)
from app.schemas.driving_behavior import (
    DrivingBehaviorCreate,
    DrivingBehaviorList,
    DrivingBehaviorOut,
)
from app.schemas.fault_log import (
    FaultLogCreate,
    FaultLogList,
    FaultLogOut,
    FaultLogUpdate,
)
from app.schemas.health import HealthOverview
from app.schemas.health_snapshot import (
    HealthItemCreate,
    HealthItemOut,
    HealthSnapshotCreate,
    HealthSnapshotList,
    HealthSnapshotOut,
)
from app.schemas.lifecycle_event import (
    LifecycleEventCreate,
    LifecycleEventList,
    LifecycleEventOut,
)
from app.schemas.maintenance import (
    MaintenanceRecordCreate,
    MaintenanceRecordList,
    MaintenanceRecordOut,
    MaintenanceScheduleCreate,
    MaintenanceScheduleList,
    MaintenanceScheduleOut,
)
from app.schemas.ownership_record import (
    OwnershipRecordCreate,
    OwnershipRecordList,
    OwnershipRecordOut,
)
from app.schemas.sensor_data import (
    SensorDataBatchCreate,
    SensorDataCreate,
    SensorDataList,
    SensorDataOut,
    SensorSeriesOut,
    SensorSeriesPoint,
)
from app.schemas.trip import (
    TripCreate,
    TripList,
    TripOut,
    TripSummary,
)
from app.schemas.user import Token, UserCreate, UserLogin, UserOut
from app.schemas.vehicle import (
    VehicleArchiveOut,
    VehicleCreate,
    VehicleList,
    VehicleOut,
    VehicleUpdate,
)
from app.schemas.vehicle_life import (
    HealthScoreBreakdown,
    LifeEventItem,
    PredictionItem,
    SimulationRequest,
    SimulationResult,
    VehicleHealthScore,
    VehicleIdentity,
    VehicleLifeRecord,
)

__all__ = [
    # Agent
    "AgentChatRequest",
    "AgentChatResponse",
    # Health overview
    "HealthOverview",
    # User
    "Token",
    "UserCreate",
    "UserLogin",
    "UserOut",
    # Vehicle
    "VehicleArchiveOut",
    "VehicleCreate",
    "VehicleList",
    "VehicleOut",
    "VehicleUpdate",
    # Lifecycle events
    "LifecycleEventCreate",
    "LifecycleEventList",
    "LifecycleEventOut",
    # Health snapshots
    "HealthItemCreate",
    "HealthItemOut",
    "HealthSnapshotCreate",
    "HealthSnapshotList",
    "HealthSnapshotOut",
    # Maintenance
    "MaintenanceRecordCreate",
    "MaintenanceRecordList",
    "MaintenanceRecordOut",
    "MaintenanceScheduleCreate",
    "MaintenanceScheduleList",
    "MaintenanceScheduleOut",
    # Driving behaviour
    "DrivingBehaviorCreate",
    "DrivingBehaviorList",
    "DrivingBehaviorOut",
    # Alerts
    "AlertCreate",
    "AlertList",
    "AlertOut",
    "AlertUpdate",
    # Ownership
    "OwnershipRecordCreate",
    "OwnershipRecordList",
    "OwnershipRecordOut",
    # Digital twin
    "DigitalTwinCreate",
    "DigitalTwinOut",
    "DigitalTwinUpdate",
    # TASK007 digital-life core schemas
    "SensorDataCreate",
    "SensorDataBatchCreate",
    "SensorDataOut",
    "SensorDataList",
    "SensorSeriesPoint",
    "SensorSeriesOut",
    "TripCreate",
    "TripOut",
    "TripList",
    "TripSummary",
    "FaultLogCreate",
    "FaultLogOut",
    "FaultLogUpdate",
    "FaultLogList",
    "DigitalStateCreate",
    "DigitalStateOut",
    "DigitalStateUpdate",
    # Vehicle digital life record + health score
    "VehicleLifeRecord",
    "VehicleIdentity",
    "VehicleHealthScore",
    "HealthScoreBreakdown",
    "LifeEventItem",
    "PredictionItem",
    "SimulationRequest",
    "SimulationResult",
]
