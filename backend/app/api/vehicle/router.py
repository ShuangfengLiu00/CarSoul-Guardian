"""Vehicle API — full digital-life archive endpoints (TASK007).

RESTful routes covering:
  /api/vehicle                         — list, create, get, update, delete
  /api/vehicle/{id}/archive            — complete archive aggregation
  /api/vehicle/{id}/lifecycle          — lifecycle timeline events
  /api/vehicle/{id}/health             — health snapshots + items
  /api/vehicle/{id}/maintenance        — records + schedules
  /api/vehicle/{id}/driving-behavior   — driving behaviour + summary
  /api/vehicle/{id}/alerts             — alerts + lifecycle management
  /api/vehicle/{id}/ownership          — ownership transfer history
  /api/vehicle/{id}/digital-twin       — digital twin metadata + telemetry
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.sensor_registry import (
    DOMAINS,
    VHS_WEIGHTED_DOMAINS,
    classify,
    get_registry,
)
from app.schemas.alert import AlertCreate, AlertList, AlertOut, AlertUpdate
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
from app.schemas.health_snapshot import (
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
from app.schemas.service_order import (
    ServiceOrderCreate,
    ServiceOrderFeedback,
    ServiceOrderList,
    ServiceOrderOut,
    ServiceOrderUpdate,
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
    SensorSnapshotDomain,
    SensorSnapshotResponse,
    SensorSnapshotSensor,
    SensorSpecOut,
)
from app.schemas.trip import (
    TripCreate,
    TripList,
    TripOut,
    TripSummary,
)
from app.schemas.vehicle import (
    VehicleArchiveOut,
    VehicleCreate,
    VehicleList,
    VehicleOut,
    VehicleUpdate,
)
from app.schemas.vehicle_life import (
    SimulationRequest,
    SimulationResult,
    VehicleHealthScore,
    VehicleLifeRecord,
)
from app.services import (
    alert_service,
    data_generator,
    digital_state_service,
    digital_twin_service,
    driving_behavior_service,
    fault_log_service,
    health_score_service,
    health_service,
    lifecycle_service,
    maintenance_service,
    ownership_service,
    sensor_data_service,
    service_order_service,
    trip_service,
    vehicle_life_service,
    vehicle_service,
)

router = APIRouter()


# ===========================================================================
# Vehicle CRUD
# ===========================================================================

@router.get("", response_model=VehicleList)
def list_vehicles(db: Session = Depends(get_db)) -> VehicleList:
    items = vehicle_service.list_vehicles(db)
    out = [VehicleOut.model_validate(v) for v in items]
    return VehicleList(items=out, total=len(out))


@router.post("", response_model=VehicleOut, status_code=201)
def create_vehicle(
    payload: VehicleCreate, db: Session = Depends(get_db)
) -> VehicleOut:
    vehicle = vehicle_service.create_vehicle(db, payload, owner_id=1)
    return VehicleOut.model_validate(vehicle)


@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)) -> VehicleOut:
    vehicle = vehicle_service.get_vehicle(db, vehicle_id)
    if vehicle is None:
        raise HTTPException(404, "Vehicle not found")
    return VehicleOut.model_validate(vehicle)


@router.put("/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    db: Session = Depends(get_db),
) -> VehicleOut:
    vehicle = vehicle_service.update_vehicle(db, vehicle_id, payload)
    if vehicle is None:
        raise HTTPException(404, "Vehicle not found")
    return VehicleOut.model_validate(vehicle)


@router.delete("/{vehicle_id}", status_code=204)
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)) -> None:
    if not vehicle_service.delete_vehicle(db, vehicle_id):
        raise HTTPException(404, "Vehicle not found")


# ===========================================================================
# Archive aggregation
# ===========================================================================

@router.get("/{vehicle_id}/archive", response_model=VehicleArchiveOut)
def get_vehicle_archive(
    vehicle_id: int, db: Session = Depends(get_db)
) -> VehicleArchiveOut:
    archive = vehicle_service.get_archive(db, vehicle_id)
    if archive is None:
        raise HTTPException(404, "Vehicle not found")
    return archive


# ===========================================================================
# Lifecycle events
# ===========================================================================

@router.get(
    "/{vehicle_id}/lifecycle",
    response_model=LifecycleEventList,
)
def list_lifecycle_events(
    vehicle_id: int,
    event_type: str | None = Query(None),
    db: Session = Depends(get_db),
) -> LifecycleEventList:
    items = lifecycle_service.list_events(db, vehicle_id, event_type)
    out = [LifecycleEventOut.model_validate(e) for e in items]
    return LifecycleEventList(items=out, total=len(out))


@router.post(
    "/{vehicle_id}/lifecycle",
    response_model=LifecycleEventOut,
    status_code=201,
)
def create_lifecycle_event(
    vehicle_id: int,
    payload: LifecycleEventCreate,
    db: Session = Depends(get_db),
) -> LifecycleEventOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    event = lifecycle_service.create_event(db, vehicle_id, payload)
    return LifecycleEventOut.model_validate(event)


@router.delete("/{vehicle_id}/lifecycle/{event_id}", status_code=204)
def delete_lifecycle_event(
    vehicle_id: int, event_id: int, db: Session = Depends(get_db)
) -> None:
    if not lifecycle_service.delete_event(db, event_id):
        raise HTTPException(404, "Event not found")


# ===========================================================================
# Health snapshots
# ===========================================================================

@router.get(
    "/{vehicle_id}/health",
    response_model=HealthSnapshotList,
)
def list_health_snapshots(
    vehicle_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> HealthSnapshotList:
    snapshots = health_service.list_snapshots(db, vehicle_id, limit)
    out = []
    for snap in snapshots:
        items = health_service.get_items(db, snap.id)
        snap_dict = {
            **{k: getattr(snap, k) for k in snap.__table__.columns.keys()},
            "items": items,
        }
        out.append(HealthSnapshotOut.model_validate(snap_dict))
    return HealthSnapshotList(items=out, total=len(out))


@router.get(
    "/{vehicle_id}/health/latest",
    response_model=HealthSnapshotOut | None,
)
def get_latest_health(
    vehicle_id: int, db: Session = Depends(get_db)
) -> HealthSnapshotOut | None:
    snap = health_service.get_latest_snapshot(db, vehicle_id)
    if snap is None:
        return None
    items = health_service.get_items(db, snap.id)
    snap_dict = {
        **{k: getattr(snap, k) for k in snap.__table__.columns.keys()},
        "items": items,
    }
    return HealthSnapshotOut.model_validate(snap_dict)


@router.post(
    "/{vehicle_id}/health",
    response_model=HealthSnapshotOut,
    status_code=201,
)
def create_health_snapshot(
    vehicle_id: int,
    payload: HealthSnapshotCreate,
    db: Session = Depends(get_db),
) -> HealthSnapshotOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    snap = health_service.create_snapshot(db, vehicle_id, payload)
    items = health_service.get_items(db, snap.id)
    snap_dict = {
        **{k: getattr(snap, k) for k in snap.__table__.columns.keys()},
        "items": items,
    }
    return HealthSnapshotOut.model_validate(snap_dict)


@router.delete("/{vehicle_id}/health/{snapshot_id}", status_code=204)
def delete_health_snapshot(
    vehicle_id: int, snapshot_id: int, db: Session = Depends(get_db)
) -> None:
    if not health_service.delete_snapshot(db, snapshot_id):
        raise HTTPException(404, "Snapshot not found")


# ===========================================================================
# Maintenance records + schedules
# ===========================================================================

@router.get(
    "/{vehicle_id}/maintenance/records",
    response_model=MaintenanceRecordList,
)
def list_maintenance_records(
    vehicle_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> MaintenanceRecordList:
    items = maintenance_service.list_records(db, vehicle_id, limit)
    out = [MaintenanceRecordOut.model_validate(r) for r in items]
    return MaintenanceRecordList(items=out, total=len(out))


@router.post(
    "/{vehicle_id}/maintenance/records",
    response_model=MaintenanceRecordOut,
    status_code=201,
)
def create_maintenance_record(
    vehicle_id: int,
    payload: MaintenanceRecordCreate,
    db: Session = Depends(get_db),
) -> MaintenanceRecordOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    record = maintenance_service.create_record(db, vehicle_id, payload)
    return MaintenanceRecordOut.model_validate(record)


@router.delete(
    "/{vehicle_id}/maintenance/records/{record_id}", status_code=204
)
def delete_maintenance_record(
    vehicle_id: int, record_id: int, db: Session = Depends(get_db)
) -> None:
    if not maintenance_service.delete_record(db, record_id):
        raise HTTPException(404, "Record not found")


@router.get(
    "/{vehicle_id}/maintenance/schedules",
    response_model=MaintenanceScheduleList,
)
def list_maintenance_schedules(
    vehicle_id: int, db: Session = Depends(get_db)
) -> MaintenanceScheduleList:
    items = maintenance_service.list_schedules(db, vehicle_id)
    out = [MaintenanceScheduleOut.model_validate(s) for s in items]
    return MaintenanceScheduleList(items=out, total=len(out))


@router.post(
    "/{vehicle_id}/maintenance/schedules",
    response_model=MaintenanceScheduleOut,
    status_code=201,
)
def create_maintenance_schedule(
    vehicle_id: int,
    payload: MaintenanceScheduleCreate,
    db: Session = Depends(get_db),
) -> MaintenanceScheduleOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    sched = maintenance_service.create_schedule(db, vehicle_id, payload)
    return MaintenanceScheduleOut.model_validate(sched)


@router.delete(
    "/{vehicle_id}/maintenance/schedules/{schedule_id}", status_code=204
)
def delete_maintenance_schedule(
    vehicle_id: int, schedule_id: int, db: Session = Depends(get_db)
) -> None:
    if not maintenance_service.delete_schedule(db, schedule_id):
        raise HTTPException(404, "Schedule not found")


# ===========================================================================
# Driving behaviour
# ===========================================================================

@router.get(
    "/{vehicle_id}/driving-behavior",
    response_model=DrivingBehaviorList,
)
def list_driving_behaviors(
    vehicle_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> DrivingBehaviorList:
    items = driving_behavior_service.list_behaviors(db, vehicle_id, days)
    out = [DrivingBehaviorOut.model_validate(b) for b in items]
    return DrivingBehaviorList(items=out, total=len(out))


@router.post(
    "/{vehicle_id}/driving-behavior",
    response_model=DrivingBehaviorOut,
    status_code=201,
)
def create_driving_behavior(
    vehicle_id: int,
    payload: DrivingBehaviorCreate,
    db: Session = Depends(get_db),
) -> DrivingBehaviorOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    behavior = driving_behavior_service.create_behavior(db, vehicle_id, payload)
    return DrivingBehaviorOut.model_validate(behavior)


@router.get("/{vehicle_id}/driving-behavior/summary")
def get_driving_behavior_summary(
    vehicle_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> dict:
    return driving_behavior_service.get_behavior_summary(db, vehicle_id, days)


@router.delete(
    "/{vehicle_id}/driving-behavior/{behavior_id}", status_code=204
)
def delete_driving_behavior(
    vehicle_id: int, behavior_id: int, db: Session = Depends(get_db)
) -> None:
    if not driving_behavior_service.delete_behavior(db, behavior_id):
        raise HTTPException(404, "Behavior record not found")


# ===========================================================================
# Alerts
# ===========================================================================

@router.get("/{vehicle_id}/alerts", response_model=AlertList)
def list_alerts(
    vehicle_id: int,
    status: str | None = Query(None),
    level: str | None = Query(None),
    db: Session = Depends(get_db),
) -> AlertList:
    items = alert_service.list_alerts(db, vehicle_id, status, level)
    out = [AlertOut.model_validate(a) for a in items]
    return AlertList(items=out, total=len(out))


@router.post(
    "/{vehicle_id}/alerts", response_model=AlertOut, status_code=201
)
def create_alert(
    vehicle_id: int,
    payload: AlertCreate,
    db: Session = Depends(get_db),
) -> AlertOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    alert = alert_service.create_alert(db, vehicle_id, payload)
    return AlertOut.model_validate(alert)


@router.patch(
    "/{vehicle_id}/alerts/{alert_id}", response_model=AlertOut
)
def update_alert(
    vehicle_id: int,
    alert_id: int,
    payload: AlertUpdate,
    db: Session = Depends(get_db),
) -> AlertOut:
    alert = alert_service.update_alert(db, alert_id, payload)
    if alert is None:
        raise HTTPException(404, "Alert not found")
    return AlertOut.model_validate(alert)


@router.delete("/{vehicle_id}/alerts/{alert_id}", status_code=204)
def delete_alert(
    vehicle_id: int, alert_id: int, db: Session = Depends(get_db)
) -> None:
    if not alert_service.delete_alert(db, alert_id):
        raise HTTPException(404, "Alert not found")


# ===========================================================================
# Ownership records
# ===========================================================================

@router.get(
    "/{vehicle_id}/ownership", response_model=OwnershipRecordList
)
def list_ownership_records(
    vehicle_id: int, db: Session = Depends(get_db)
) -> OwnershipRecordList:
    items = ownership_service.list_records(db, vehicle_id)
    out = [OwnershipRecordOut.model_validate(r) for r in items]
    return OwnershipRecordList(items=out, total=len(out))


@router.post(
    "/{vehicle_id}/ownership",
    response_model=OwnershipRecordOut,
    status_code=201,
)
def create_ownership_record(
    vehicle_id: int,
    payload: OwnershipRecordCreate,
    db: Session = Depends(get_db),
) -> OwnershipRecordOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    record = ownership_service.create_record(db, vehicle_id, payload)
    return OwnershipRecordOut.model_validate(record)


@router.delete(
    "/{vehicle_id}/ownership/{record_id}", status_code=204
)
def delete_ownership_record(
    vehicle_id: int, record_id: int, db: Session = Depends(get_db)
) -> None:
    if not ownership_service.delete_record(db, record_id):
        raise HTTPException(404, "Ownership record not found")


# ===========================================================================
# Service orders (after-sales closed loop — §3A.1)
# ===========================================================================

@router.get(
    "/{vehicle_id}/service-orders",
    response_model=ServiceOrderList,
)
def list_service_orders(
    vehicle_id: int,
    status: str | None = Query(None),
    db: Session = Depends(get_db),
) -> ServiceOrderList:
    """列出车辆的售后工单，可按状态过滤。"""
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    items = service_order_service.list_orders(db, vehicle_id, status=status)
    out = [ServiceOrderOut.model_validate(o) for o in items]
    return ServiceOrderList(items=out, total=len(out))


@router.get(
    "/{vehicle_id}/service-orders/{order_id}",
    response_model=ServiceOrderOut,
)
def get_service_order(
    vehicle_id: int,
    order_id: int,
    db: Session = Depends(get_db),
) -> ServiceOrderOut:
    """查询单个售后工单详情（含完整状态历史）。"""
    order = service_order_service.get_order(db, order_id)
    if order is None or order.vehicle_id != vehicle_id:
        raise HTTPException(404, "Service order not found")
    return ServiceOrderOut.model_validate(order)


@router.post(
    "/{vehicle_id}/service-orders",
    response_model=ServiceOrderOut,
    status_code=201,
)
def create_service_order(
    vehicle_id: int,
    payload: ServiceOrderCreate,
    db: Session = Depends(get_db),
) -> ServiceOrderOut:
    """创建售后工单（通常由 Agent 诊断触发）。"""
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    order = service_order_service.create_order(db, vehicle_id, payload)
    return ServiceOrderOut.model_validate(order)


@router.patch(
    "/{vehicle_id}/service-orders/{order_id}",
    response_model=ServiceOrderOut,
)
def advance_service_order(
    vehicle_id: int,
    order_id: int,
    payload: ServiceOrderUpdate,
    db: Session = Depends(get_db),
) -> ServiceOrderOut:
    """推进工单状态（created→booked→in_service→done→closed）。"""
    order = service_order_service.get_order(db, order_id)
    if order is None or order.vehicle_id != vehicle_id:
        raise HTTPException(404, "Service order not found")
    try:
        order = service_order_service.advance_order(db, order_id, payload)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    if order is None:
        raise HTTPException(404, "Service order not found")
    return ServiceOrderOut.model_validate(order)


@router.post(
    "/{vehicle_id}/service-orders/{order_id}/feedback",
    response_model=ServiceOrderOut,
)
def submit_service_feedback(
    vehicle_id: int,
    order_id: int,
    payload: ServiceOrderFeedback,
    db: Session = Depends(get_db),
) -> ServiceOrderOut:
    """提交售后反馈（confirmed/false_alarm/no_event/partial）。"""
    order = service_order_service.get_order(db, order_id)
    if order is None or order.vehicle_id != vehicle_id:
        raise HTTPException(404, "Service order not found")
    try:
        order = service_order_service.submit_feedback(db, order_id, payload)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    if order is None:
        raise HTTPException(404, "Service order not found")
    return ServiceOrderOut.model_validate(order)


@router.delete(
    "/{vehicle_id}/service-orders/{order_id}", status_code=204
)
def delete_service_order(
    vehicle_id: int, order_id: int, db: Session = Depends(get_db)
) -> None:
    if not service_order_service.delete_order(db, order_id):
        raise HTTPException(404, "Service order not found")


# ===========================================================================
# Digital twin
# ===========================================================================

@router.get(
    "/{vehicle_id}/digital-twin", response_model=DigitalTwinOut | None
)
def get_digital_twin(
    vehicle_id: int, db: Session = Depends(get_db)
) -> DigitalTwinOut | None:
    twin = digital_twin_service.get_twin(db, vehicle_id)
    if twin is None:
        return None
    return DigitalTwinOut.model_validate(twin)


@router.post(
    "/{vehicle_id}/digital-twin",
    response_model=DigitalTwinOut,
    status_code=201,
)
def create_digital_twin(
    vehicle_id: int,
    payload: DigitalTwinCreate,
    db: Session = Depends(get_db),
) -> DigitalTwinOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    try:
        twin = digital_twin_service.create_twin(db, vehicle_id, payload)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    return DigitalTwinOut.model_validate(twin)


@router.patch(
    "/{vehicle_id}/digital-twin", response_model=DigitalTwinOut
)
def update_digital_twin(
    vehicle_id: int,
    payload: DigitalTwinUpdate,
    db: Session = Depends(get_db),
) -> DigitalTwinOut:
    twin = digital_twin_service.update_twin(db, vehicle_id, payload)
    if twin is None:
        raise HTTPException(404, "Digital twin not found")
    return DigitalTwinOut.model_validate(twin)


@router.post(
    "/{vehicle_id}/digital-twin/telemetry",
    response_model=DigitalTwinOut,
)
def push_telemetry(
    vehicle_id: int,
    telemetry: dict,
    db: Session = Depends(get_db),
) -> DigitalTwinOut:
    twin = digital_twin_service.sync_telemetry(db, vehicle_id, telemetry)
    if twin is None:
        raise HTTPException(404, "Digital twin not found")
    return DigitalTwinOut.model_validate(twin)


@router.delete(
    "/{vehicle_id}/digital-twin", status_code=204
)
def delete_digital_twin(
    vehicle_id: int, db: Session = Depends(get_db)
) -> None:
    if not digital_twin_service.delete_twin(db, vehicle_id):
        raise HTTPException(404, "Digital twin not found")


# ===========================================================================
# Sensor data (IoT telemetry)
# ===========================================================================

@router.get(
    "/{vehicle_id}/sensors", response_model=SensorDataList
)
def list_sensor_readings(
    vehicle_id: int,
    sensor_type: str | None = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> SensorDataList:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    rows = sensor_data_service.list_readings(
        db, vehicle_id, sensor_type=sensor_type, limit=limit
    )
    out = [SensorDataOut.model_validate(r) for r in rows]
    return SensorDataList(items=out, total=len(out))


@router.get("/{vehicle_id}/sensors/types")
def list_sensor_types(
    vehicle_id: int, db: Session = Depends(get_db)
) -> dict:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    types = sensor_data_service.list_sensor_types(db, vehicle_id)
    return {"vehicle_id": vehicle_id, "sensor_types": types}


@router.get(
    "/{vehicle_id}/sensors/series", response_model=SensorSeriesOut
)
def get_sensor_series(
    vehicle_id: int,
    sensor_type: str = Query(..., description="传感器类型"),
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
) -> SensorSeriesOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    return sensor_data_service.get_series(db, vehicle_id, sensor_type, hours)


# Status → sub-score used by the snapshot's self-contained baseline VHS.
_STATUS_SCORE = {"normal": 100.0, "warn": 70.0, "crit": 40.0}


def _grade(score: float) -> tuple[str, str]:
    """VHS grading thresholds (arch doc §3.4)."""
    if score >= 95:
        return "gold", "黄金车况"
    if score >= 80:
        return "excellent", "优秀"
    if score >= 60:
        return "general", "一般"
    return "risk", "风险车辆"


@router.get(
    "/{vehicle_id}/sensors/snapshot", response_model=SensorSnapshotResponse
)
def get_sensor_snapshot(
    vehicle_id: int,
    domain: str | None = Query(
        None, description="逗号分隔的域筛选，如 battery,motor；缺省返回全部 6 域"
    ),
    include_spec: bool = Query(True, description="是否返回范围/阈值/采样率元数据"),
    db: Session = Depends(get_db),
) -> SensorSnapshotResponse:
    """全车传感器当前快照 —— 模拟面板的基线（arch doc §4.5.1）。

    58 项信号按 6 个域分组返回，每项带 registry spec、当前值与 normal/warn/crit
    状态；`baseline` 是一个自包含的简化 VHS 基线分；`provenance` 是 GOAI 溯源信封。
    """
    vehicle = vehicle_service.get_vehicle(db, vehicle_id)
    if vehicle is None:
        raise HTTPException(404, "Vehicle not found")
    if sensor_data_service.count(db, vehicle_id) == 0:
        raise HTTPException(
            409,
            "该车辆暂无传感器数据，请先调用 POST /api/vehicle/{vehicle_id}/simulate "
            "生成模拟数据",
        )

    energy_type = vehicle.fuel_type or "electric"

    wanted: set[str] | None = None
    if domain:
        wanted = {d.strip() for d in domain.split(",") if d.strip()}
        unknown = wanted - set(DOMAINS)
        if unknown:
            raise HTTPException(400, f"未知的传感器域: {','.join(sorted(unknown))}")

    specs = [
        s for s in get_registry(energy_type)
        if wanted is None or s.domain in wanted
    ]

    grouped: dict[str, list[SensorSnapshotSensor]] = {}
    for spec in specs:
        row = sensor_data_service.latest_reading(db, vehicle_id, spec.sensor_type)
        if row is not None:
            value = float(row.sensor_value)
            unit = row.unit or spec.unit
            source = "seed"
        else:
            value = float(spec.baseline)
            unit = spec.unit
            source = "default"
        grouped.setdefault(spec.domain, []).append(
            SensorSnapshotSensor(
                sensor_type=spec.sensor_type,
                label=spec.label,
                value=round(value, 4),
                unit=unit,
                spec=SensorSpecOut(
                    min=spec.min,
                    max=spec.max,
                    warn_low=spec.warn_low,
                    warn_high=spec.warn_high,
                    crit_low=spec.crit_low,
                    crit_high=spec.crit_high,
                    step=spec.step,
                    sample_hz_can=spec.sample_hz_can,
                    sample_hz_upload=spec.sample_hz_upload,
                    adjustable=spec.adjustable,
                ) if include_spec else None,
                status=classify(spec, value),
                source=source,
            )
        )

    domains_out: list[SensorSnapshotDomain] = []
    domain_scores: dict[str, float] = {}
    for key, meta in DOMAINS.items():
        sensors = grouped.get(key)
        if not sensors:
            continue
        domain_scores[key] = round(
            sum(_STATUS_SCORE[s.status] for s in sensors) / len(sensors), 1
        )
        domains_out.append(SensorSnapshotDomain(
            domain=key,
            label=meta["label"],
            vhs_component=meta["vhs_component"],
            vhs_weight=meta["vhs_weight"],
            sensors=sensors,
        ))

    # Weighted over the sensor-driven VHS domains only. Driving / Maintenance
    # (0.15 each) are not sensor-derived, so the remaining weights are
    # re-normalised to 1.0 instead of capping the score at 0.70.
    weighted = [
        (DOMAINS[k]["vhs_weight"], v)
        for k, v in domain_scores.items()
        if k in VHS_WEIGHTED_DOMAINS
    ]
    total_weight = sum(w for w, _ in weighted)
    if total_weight > 0:
        raw = sum(w * v for w, v in weighted) / total_weight
    elif domain_scores:
        raw = sum(domain_scores.values()) / len(domain_scores)
    else:
        raw = 0.0
    health_score = round(max(0.0, min(100.0, raw)), 1)
    grade, grade_label = _grade(health_score)

    now = datetime.utcnow()
    return SensorSnapshotResponse(
        vehicle_id=vehicle_id,
        as_of=now,
        energy_type=energy_type,
        domains=domains_out,
        baseline={
            "health_score": health_score,
            "grade": grade,
            "grade_label": grade_label,
            "breakdown": domain_scores,
        },
        provenance={
            "data_source": "seed",
            "demo_mode": True,
            "badge_level": "L2b",
            "origin": "seed:init_db",
            "as_of": now.isoformat() + "Z",
        },
    )


@router.post(
    "/{vehicle_id}/sensors", response_model=SensorDataOut, status_code=201
)
def create_sensor_reading(
    vehicle_id: int,
    payload: SensorDataCreate,
    db: Session = Depends(get_db),
) -> SensorDataOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    row = sensor_data_service.create_reading(db, vehicle_id, payload)
    return SensorDataOut.model_validate(row)


@router.post(
    "/{vehicle_id}/sensors/batch",
    response_model=SensorDataList,
    status_code=201,
)
def create_sensor_readings_batch(
    vehicle_id: int,
    payload: SensorDataBatchCreate,
    db: Session = Depends(get_db),
) -> SensorDataList:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    rows = sensor_data_service.create_readings_batch(db, vehicle_id, payload)
    out = [SensorDataOut.model_validate(r) for r in rows]
    return SensorDataList(items=out, total=len(out))


# ===========================================================================
# Trips
# ===========================================================================

@router.get("/{vehicle_id}/trips", response_model=TripList)
def list_trips(
    vehicle_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> TripList:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    rows = trip_service.list_trips(db, vehicle_id, limit)
    out = [TripOut.model_validate(t) for t in rows]
    return TripList(items=out, total=len(out))


@router.get("/{vehicle_id}/trips/summary", response_model=TripSummary)
def get_trip_summary(
    vehicle_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
) -> TripSummary:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    return trip_service.get_summary(db, vehicle_id, days)


@router.post(
    "/{vehicle_id}/trips", response_model=TripOut, status_code=201
)
def create_trip(
    vehicle_id: int,
    payload: TripCreate,
    db: Session = Depends(get_db),
) -> TripOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    trip = trip_service.create_trip(db, vehicle_id, payload)
    return TripOut.model_validate(trip)


@router.delete("/{vehicle_id}/trips/{trip_id}", status_code=204)
def delete_trip(
    vehicle_id: int, trip_id: int, db: Session = Depends(get_db)
) -> None:
    if not trip_service.delete_trip(db, trip_id):
        raise HTTPException(404, "Trip not found")


# ===========================================================================
# Fault logs
# ===========================================================================

@router.get("/{vehicle_id}/faults", response_model=FaultLogList)
def list_faults(
    vehicle_id: int,
    repair_status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> FaultLogList:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    rows = fault_log_service.list_faults(
        db, vehicle_id, repair_status=repair_status, limit=limit
    )
    out = [FaultLogOut.model_validate(f) for f in rows]
    return FaultLogList(items=out, total=len(out))


@router.post(
    "/{vehicle_id}/faults", response_model=FaultLogOut, status_code=201
)
def create_fault(
    vehicle_id: int,
    payload: FaultLogCreate,
    db: Session = Depends(get_db),
) -> FaultLogOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    fault = fault_log_service.create_fault(db, vehicle_id, payload)
    return FaultLogOut.model_validate(fault)


@router.patch(
    "/{vehicle_id}/faults/{fault_id}", response_model=FaultLogOut
)
def update_fault(
    vehicle_id: int,
    fault_id: int,
    payload: FaultLogUpdate,
    db: Session = Depends(get_db),
) -> FaultLogOut:
    fault = fault_log_service.update_fault(db, fault_id, payload)
    if fault is None:
        raise HTTPException(404, "Fault not found")
    return FaultLogOut.model_validate(fault)


@router.delete("/{vehicle_id}/faults/{fault_id}", status_code=204)
def delete_fault(
    vehicle_id: int, fault_id: int, db: Session = Depends(get_db)
) -> None:
    if not fault_log_service.delete_fault(db, fault_id):
        raise HTTPException(404, "Fault not found")


# ===========================================================================
# Digital state (real-time)
# ===========================================================================

@router.get(
    "/{vehicle_id}/digital-state", response_model=DigitalStateOut | None
)
def get_digital_state(
    vehicle_id: int, db: Session = Depends(get_db)
) -> DigitalStateOut | None:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    state = digital_state_service.get_state(db, vehicle_id)
    if state is None:
        return None
    return DigitalStateOut.model_validate(state)


@router.put(
    "/{vehicle_id}/digital-state", response_model=DigitalStateOut
)
def upsert_digital_state(
    vehicle_id: int,
    payload: DigitalStateCreate,
    db: Session = Depends(get_db),
) -> DigitalStateOut:
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    state = digital_state_service.upsert_state(db, vehicle_id, payload)
    return DigitalStateOut.model_validate(state)


@router.patch(
    "/{vehicle_id}/digital-state", response_model=DigitalStateOut
)
def patch_digital_state(
    vehicle_id: int,
    payload: DigitalStateUpdate,
    db: Session = Depends(get_db),
) -> DigitalStateOut:
    state = digital_state_service.patch_state(db, vehicle_id, payload)
    if state is None:
        raise HTTPException(404, "Digital state not found")
    return DigitalStateOut.model_validate(state)


@router.delete(
    "/{vehicle_id}/digital-state", status_code=204
)
def delete_digital_state(
    vehicle_id: int, db: Session = Depends(get_db)
) -> None:
    if not digital_state_service.delete_state(db, vehicle_id):
        raise HTTPException(404, "Digital state not found")


# ===========================================================================
# Vehicle digital life record (flagship read model)
# ===========================================================================

@router.get(
    "/{vehicle_id}/life", response_model=VehicleLifeRecord
)
def get_vehicle_life(
    vehicle_id: int, db: Session = Depends(get_db)
) -> VehicleLifeRecord:
    """查询车辆数字生命档案 — 车辆数字孪生的核心叙事视图."""
    record = vehicle_life_service.get_life_record(db, vehicle_id)
    if record is None:
        raise HTTPException(404, "Vehicle not found")
    return record


@router.get(
    "/{vehicle_id}/health-score", response_model=VehicleHealthScore
)
def get_health_score(
    vehicle_id: int, db: Session = Depends(get_db)
) -> VehicleHealthScore:
    """计算车辆健康评分 (VHS) — 加权健康指数模型."""
    score = health_score_service.compute_health_score(db, vehicle_id)
    if score is None:
        raise HTTPException(404, "Vehicle not found")
    return score


# ===========================================================================
# Mock data generator / digital-twin simulator
# ===========================================================================

@router.post(
    "/{vehicle_id}/simulate", response_model=SimulationResult
)
def simulate_vehicle(
    vehicle_id: int,
    payload: SimulationRequest,
    db: Session = Depends(get_db),
) -> SimulationResult:
    """生成模拟数据（传感器/行程/故障）并刷新实时数字状态."""
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    # Force the vehicle_id from the path.
    payload = payload.model_copy(update={"vehicle_id": vehicle_id})
    return data_generator.run_simulation(db, payload)


@router.post("/{vehicle_id}/simulate/quick", response_model=SimulationResult)
def simulate_vehicle_quick(
    vehicle_id: int,
    sensor_points: int = Query(24, ge=1, le=500),
    trip_count: int = Query(5, ge=0, le=50),
    fault_count: int = Query(0, ge=0, le=10),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
) -> SimulationResult:
    """快速生成模拟数据（无需请求体，全部走 query 参数）."""
    if vehicle_service.get_vehicle(db, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    req = SimulationRequest(
        vehicle_id=vehicle_id,
        sensor_points=sensor_points,
        trip_count=trip_count,
        fault_count=fault_count,
        days=days,
        update_digital_state=True,
    )
    return data_generator.run_simulation(db, req)
