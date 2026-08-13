"""T-BOX 适配层 REST 接口。

端点（SPEC §5.1，挂载前缀 /api/v1/tbox）：
  GET  /telemetry/{signal_id}?vehicle_id=CS001   单信号读取
  POST /telemetry                                  批量读取
  GET  /telemetry/group/{group}?vehicle_id=CS001   按组读取
  GET  /dtc?vehicle_id=CS001                       DTC 读取

路由层只做参数校验 + 调适配器 + 组装响应，不含业务逻辑（C-08 分层）。
单信号响应直接平铺 TelemetryReading 字段，满足 SPEC §12.2 冒烟测试。
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.adapters.tbox_adapter import DTCReading, TelemetryReading, TBoxAdapter

router = APIRouter()


class TelemetryOut(BaseModel):
    signal_id: str
    value: object | None
    unit: str
    timestamp: float
    data_source: str
    confidence: float
    quality_flags: list[str] = Field(default_factory=list)


class DTCOut(BaseModel):
    code: str
    system: str
    severity: str
    description: str
    timestamp: float
    data_source: str
    confidence: float


class BatchRequest(BaseModel):
    vehicle_id: str = "CS001"
    signal_ids: list[str]


class BatchResponse(BaseModel):
    vehicle_id: str
    count: int
    readings: list[TelemetryOut]


class GroupResponse(BaseModel):
    vehicle_id: str
    group: str
    count: int
    readings: list[TelemetryOut]


class DTCResponse(BaseModel):
    vehicle_id: str
    count: int
    dtcs: list[DTCOut]


def _to_telemetry_out(r: TelemetryReading) -> TelemetryOut:
    return TelemetryOut(
        signal_id=r.signal_id,
        value=r.value,
        unit=r.unit,
        timestamp=r.timestamp,
        data_source=r.data_source.value,
        confidence=r.confidence,
        quality_flags=list(r.quality_flags),
    )


def _to_dtc_out(d: DTCReading) -> DTCOut:
    return DTCOut(
        code=d.code,
        system=d.system,
        severity=d.severity,
        description=d.description,
        timestamp=d.timestamp,
        data_source=d.data_source.value,
        confidence=d.confidence,
    )


@router.get(
    "/telemetry/{signal_id}",
    response_model=TelemetryOut,
    summary="读取单个 T-BOX 信号（4 级降级）",
)
def read_signal(
    signal_id: str,
    vehicle_id: str = Query("CS001", description="车辆 ID"),
) -> TelemetryOut:
    adapter = TBoxAdapter(vehicle_id=vehicle_id)
    return _to_telemetry_out(adapter.read(signal_id))


@router.post(
    "/telemetry",
    response_model=BatchResponse,
    summary="批量读取 T-BOX 信号",
)
def read_batch(payload: BatchRequest) -> BatchResponse:
    adapter = TBoxAdapter(vehicle_id=payload.vehicle_id)
    readings = [_to_telemetry_out(r) for r in adapter.read_batch(payload.signal_ids)]
    return BatchResponse(
        vehicle_id=payload.vehicle_id, count=len(readings), readings=readings
    )


@router.get(
    "/telemetry/group/{group}",
    response_model=GroupResponse,
    summary="按信号组读取 T-BOX 信号",
)
def read_group(
    group: str,
    vehicle_id: str = Query("CS001", description="车辆 ID"),
) -> GroupResponse:
    adapter = TBoxAdapter(vehicle_id=vehicle_id)
    readings = [_to_telemetry_out(r) for r in adapter.read_group(group)]
    return GroupResponse(
        vehicle_id=vehicle_id, group=group, count=len(readings), readings=readings
    )


@router.get(
    "/dtc",
    response_model=DTCResponse,
    summary="读取异常码 DTC",
)
def read_dtc(
    vehicle_id: str = Query("CS001", description="车辆 ID"),
) -> DTCResponse:
    adapter = TBoxAdapter(vehicle_id=vehicle_id)
    dtcs = [_to_dtc_out(d) for d in adapter.get_dtc()]
    return DTCResponse(vehicle_id=vehicle_id, count=len(dtcs), dtcs=dtcs)
