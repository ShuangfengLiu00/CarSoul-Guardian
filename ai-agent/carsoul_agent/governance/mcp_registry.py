"""MCP Registry — 车辆能力接口注册中心 (§8 MCP Layer).

Implements the Model Context Protocol (MCP) interface registry for the
Governance Architecture. Each MCP interface represents a callable
vehicle-data or knowledge endpoint that agents may invoke, e.g.:

    vehicle.sensor.read   → GET /api/v1/vehicle/sensors
    vehicle.battery.read  → GET /api/v1/vehicle/battery
    knowledge.search      → POST /api/v1/knowledge/search

The registry enforces:

  - **Permission scoping** — each interface declares the permission an
    agent must hold to call it (links to ``permissions.py``).
  - **Category grouping** — interfaces are grouped as
    ``vehicle`` / ``knowledge`` / ``external``.
  - **Input/output contracts** — parameter and response schemas for
    pre-call validation.

This mirrors the pattern used by ``registry.py``: a dataclass plus a
central registry with lookup helpers and a singleton instance seeded by
``register_mcp_interfaces()``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MCPInterface:
    """Metadata for a registered MCP interface (§8 data structure).

    Mirrors the interface schema in the governance document:

        {
          "interface_id": "vehicle.sensor.read",
          "name": "Vehicle Sensor Read",
          "method": "GET",
          "path": "/api/v1/vehicle/sensors",
          "required_permission": "read_vehicle_sensors",
          "category": "vehicle"
        }
    """

    interface_id: str  # e.g. "vehicle.sensor.read"
    name: str
    description: str
    method: str  # GET / POST.
    path: str  # API path.
    input_params: dict = field(default_factory=dict)  # Request parameters schema.
    output_format: dict = field(default_factory=dict)  # Response format schema.
    required_permission: str = ""  # Permission required to call this interface.
    category: str = "vehicle"  # vehicle / knowledge / external.
    registered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a dict suitable for API responses."""
        return {
            "interface_id": self.interface_id,
            "name": self.name,
            "description": self.description,
            "method": self.method,
            "path": self.path,
            "input_params": self.input_params,
            "output_format": self.output_format,
            "required_permission": self.required_permission,
            "category": self.category,
            "registered_at": self.registered_at,
        }


class MCPRegistry:
    """Central registry for MCP interfaces — discovery and lookup.

    Extends the governance layer with:
      - Interface registration with rich schema metadata.
      - Discovery by id, by category, or by required permission.
      - Pre-call validation support (permission + schema).
    """

    def __init__(self) -> None:
        self._interfaces: dict[str, MCPInterface] = {}

    # ---- Registration ------------------------------------------------
    def register(
        self,
        interface_id: str,
        name: str,
        description: str,
        method: str,
        path: str,
        input_params: dict | None = None,
        output_format: dict | None = None,
        required_permission: str = "",
        category: str = "vehicle",
    ) -> MCPInterface:
        """Register or update an MCP interface."""
        iface = MCPInterface(
            interface_id=interface_id,
            name=name,
            description=description,
            method=method,
            path=path,
            input_params=input_params or {},
            output_format=output_format or {},
            required_permission=required_permission,
            category=category,
        )
        self._interfaces[interface_id] = iface
        logger.info(
            "MCP interface registered: %s (%s %s) perm=%s",
            interface_id, method, path, required_permission or "none",
        )
        return iface

    # ---- Lookup ------------------------------------------------------
    def get(self, interface_id: str) -> MCPInterface | None:
        """Return the interface metadata, or None if not found."""
        return self._interfaces.get(interface_id)

    def all_interfaces(self) -> list[MCPInterface]:
        """Return all registered interfaces."""
        return list(self._interfaces.values())

    def names(self) -> list[str]:
        """Return all registered interface ids."""
        return list(self._interfaces.keys())

    def find_by_category(self, category: str) -> list[MCPInterface]:
        """Find all interfaces in a given category."""
        return [i for i in self._interfaces.values() if i.category == category]

    def find_by_permission(self, permission: str) -> list[MCPInterface]:
        """Find all interfaces that require a given permission.

        An interface with an empty ``required_permission`` is considered
        publicly callable and is NOT returned here (use ``find_by_category``
        or ``all_interfaces`` to discover them).
        """
        return [
            i for i in self._interfaces.values()
            if i.required_permission == permission
        ]

    # ---- Serialisation for API/frontend -----------------------------
    def to_dict(self) -> dict[str, Any]:
        """Serialise the entire registry for API/frontend."""
        return {
            "interface_count": len(self._interfaces),
            "categories": sorted({i.category for i in self._interfaces.values()}),
            "interfaces": [i.to_dict() for i in self._interfaces.values()],
        }


# ------------------------------------------------------------------ #
#  Singleton instance
# ------------------------------------------------------------------ #
mcp_registry = MCPRegistry()


def register_mcp_interfaces() -> None:
    """Pre-register all CarSoul MCP interfaces into the registry.

    Called once at startup to populate the registry with ~15 interfaces
    covering vehicle sensors, subsystem reads, maintenance, faults,
    digital twin, risk prediction, and knowledge access.
    """
    # --- Vehicle sensor interfaces ---
    mcp_registry.register(
        interface_id="vehicle.sensor.read",
        name="Vehicle Sensor Read",
        description="读取车辆全量传感器实时数据。",
        method="GET",
        path="/api/v1/vehicle/sensors",
        input_params={"window_seconds": "int", "sensor_types": "list[str]"},
        output_format={"sensors": "list[dict]", "timestamp": "str"},
        required_permission="read_vehicle_sensors",
        category="vehicle",
    )
    mcp_registry.register(
        interface_id="vehicle.health.query",
        name="Vehicle Health Query",
        description="查询车辆整体健康评分与状态摘要。",
        method="GET",
        path="/api/v1/vehicle/health",
        input_params={"vehicle_id": "str"},
        output_format={"health_score": "float", "grade": "str", "summary": "dict"},
        required_permission="read_vehicle_health",
        category="vehicle",
    )

    # --- Battery interfaces ---
    mcp_registry.register(
        interface_id="vehicle.battery.read",
        name="Vehicle Battery Read",
        description="读取电池组状态（SOC、SOH、温度、电压等）。",
        method="GET",
        path="/api/v1/vehicle/battery",
        input_params={"vehicle_id": "str"},
        output_format={"soc": "float", "soh": "float", "temperature": "float", "voltage": "float"},
        required_permission="read_vehicle_battery",
        category="vehicle",
    )

    # --- Engine / powertrain interfaces ---
    mcp_registry.register(
        interface_id="vehicle.engine.read",
        name="Vehicle Engine Read",
        description="读取发动机/电机运行状态参数。",
        method="GET",
        path="/api/v1/vehicle/engine",
        input_params={"vehicle_id": "str"},
        output_format={"rpm": "int", "temp": "float", "load": "float", "status": "str"},
        required_permission="read_vehicle_engine",
        category="vehicle",
    )

    # --- Brake interfaces ---
    mcp_registry.register(
        interface_id="vehicle.brake.read",
        name="Vehicle Brake Read",
        description="读取制动系统状态（刹车片、制动液等）。",
        method="GET",
        path="/api/v1/vehicle/brake",
        input_params={"vehicle_id": "str"},
        output_format={"pad_remaining_km": "int", "fluid_level": "float", "status": "str"},
        required_permission="read_vehicle_brake",
        category="vehicle",
    )

    # --- Tire interfaces ---
    mcp_registry.register(
        interface_id="vehicle.tire.read",
        name="Vehicle Tire Read",
        description="读取轮胎状态（胎压、胎纹深度等）。",
        method="GET",
        path="/api/v1/vehicle/tire",
        input_params={"vehicle_id": "str"},
        output_format={"tread_mm": "float", "pressure": "dict", "status": "str"},
        required_permission="read_vehicle_tire",
        category="vehicle",
    )

    # --- Driving behavior interfaces ---
    mcp_registry.register(
        interface_id="vehicle.driving_behavior.read",
        name="Vehicle Driving Behavior Read",
        description="读取驾驶行为数据（急加速、急刹车、超速等）。",
        method="GET",
        path="/api/v1/vehicle/driving-behavior",
        input_params={"vehicle_id": "str", "time_range": "str"},
        output_format={"behaviors": "list[dict]", "safety_score": "float"},
        required_permission="read_driving_behavior",
        category="vehicle",
    )

    # --- Maintenance interfaces ---
    mcp_registry.register(
        interface_id="vehicle.maintenance.search",
        name="Vehicle Maintenance Search",
        description="搜索车辆保养历史记录。",
        method="GET",
        path="/api/v1/vehicle/maintenance",
        input_params={"vehicle_id": "str", "limit": "int"},
        output_format={"records": "list[dict]", "total": "int"},
        required_permission="read_maintenance_history",
        category="vehicle",
    )

    # --- Fault interfaces ---
    mcp_registry.register(
        interface_id="vehicle.fault.query",
        name="Vehicle Fault Query",
        description="查询车辆当前与历史故障码。",
        method="GET",
        path="/api/v1/vehicle/faults",
        input_params={"vehicle_id": "str", "include_history": "bool"},
        output_format={"active_codes": "list[str]", "history": "list[dict]"},
        required_permission="read_fault_codes",
        category="vehicle",
    )

    # --- Alert interfaces ---
    mcp_registry.register(
        interface_id="vehicle.alert.list",
        name="Vehicle Alert List",
        description="列出车辆当前活跃告警列表。",
        method="GET",
        path="/api/v1/vehicle/alerts",
        input_params={"vehicle_id": "str", "severity": "str"},
        output_format={"alerts": "list[dict]", "count": "int"},
        required_permission="read_vehicle_health",
        category="vehicle",
    )

    # --- Lifecycle / digital twin interfaces ---
    mcp_registry.register(
        interface_id="vehicle.lifecycle.events",
        name="Vehicle Lifecycle Events",
        description="查询车辆生命周期事件（数字生命档案）。",
        method="GET",
        path="/api/v1/vehicle/lifecycle/events",
        input_params={"vehicle_id": "str", "event_type": "str"},
        output_format={"events": "list[dict]", "total": "int"},
        required_permission="read_vehicle_all",
        category="vehicle",
    )
    mcp_registry.register(
        interface_id="vehicle.digital_twin.read",
        name="Vehicle Digital Twin Read",
        description="读取车辆数字孪生模型快照。",
        method="GET",
        path="/api/v1/vehicle/digital-twin",
        input_params={"vehicle_id": "str", "snapshot": "bool"},
        output_format={"digital_twin": "dict", "last_updated": "str"},
        required_permission="read_vehicle_all",
        category="vehicle",
    )

    # --- Risk prediction interfaces ---
    mcp_registry.register(
        interface_id="vehicle.risk.predict",
        name="Vehicle Risk Predict",
        description="调用车辆风险预测模型，获取未来风险预估。",
        method="POST",
        path="/api/v1/vehicle/risk/predict",
        input_params={"vehicle_id": "str", "horizon_hours": "int", "scenario": "str"},
        output_format={"risk_level": "str", "probability": "float", "eta_hours": "float"},
        required_permission="read_risk_history",
        category="vehicle",
    )

    # --- Knowledge interfaces ---
    mcp_registry.register(
        interface_id="knowledge.search",
        name="Knowledge Search",
        description="在车辆知识库中检索相关知识条目。",
        method="POST",
        path="/api/v1/knowledge/search",
        input_params={"query": "str", "top_k": "int", "filters": "dict"},
        output_format={"results": "list[dict]", "total": "int"},
        required_permission="read_knowledge_base",
        category="knowledge",
    )
    mcp_registry.register(
        interface_id="knowledge.ingest",
        name="Knowledge Ingest",
        description="向车辆知识库写入新知识条目。",
        method="POST",
        path="/api/v1/knowledge/ingest",
        input_params={"source": "str", "content": "str", "metadata": "dict"},
        output_format={"entry_id": "str", "status": "str"},
        required_permission="read_knowledge_base",
        category="knowledge",
    )

    logger.info(
        "MCP registry initialised with %d interfaces", len(mcp_registry.names())
    )
