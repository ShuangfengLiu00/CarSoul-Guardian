"""Permission Model — Agent 权限治理 (§9).

Implements the least-privilege principle from the Governance Architecture:

    Agent → Role → Permission → Data

Each agent declares the data resources it may access. The permission
checker enforces this at runtime so a battery expert can never read
user location or payment data, for example.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class Permission:
    """Canonical permission constants for CarSoul agents."""

    # --- Vehicle data ---
    READ_VEHICLE_ALL = "read_vehicle_all"
    READ_VEHICLE_SENSORS = "read_vehicle_sensors"
    READ_VEHICLE_HEALTH = "read_vehicle_health"
    READ_VEHICLE_BATTERY = "read_vehicle_battery"
    READ_VEHICLE_ENGINE = "read_vehicle_engine"
    READ_VEHICLE_BRAKE = "read_vehicle_brake"
    READ_VEHICLE_TIRE = "read_vehicle_tire"
    READ_DRIVING_BEHAVIOR = "read_driving_behavior"
    READ_RISK_HISTORY = "read_risk_history"
    READ_MAINTENANCE_HISTORY = "read_maintenance_history"
    READ_FAULT_CODES = "read_fault_codes"

    # --- Knowledge ---
    READ_KNOWLEDGE_BASE = "read_knowledge_base"
    READ_ALL_AGENT_OUTPUTS = "read_all_agent_outputs"

    # --- Write ---
    WRITE_DIGITAL_TWIN = "write_digital_twin"
    SEND_REMINDER = "send_reminder"

    # --- Admin ---
    INVOKE_ALL_AGENTS = "invoke_all_agents"

    # --- Explicitly denied (never granted) ---
    # read_user_location, read_payment_data, read_personal_info

    ALL = {
        READ_VEHICLE_ALL, READ_VEHICLE_SENSORS, READ_VEHICLE_HEALTH,
        READ_VEHICLE_BATTERY, READ_VEHICLE_ENGINE, READ_VEHICLE_BRAKE,
        READ_VEHICLE_TIRE, READ_DRIVING_BEHAVIOR, READ_RISK_HISTORY,
        READ_MAINTENANCE_HISTORY, READ_FAULT_CODES,
        READ_KNOWLEDGE_BASE, READ_ALL_AGENT_OUTPUTS,
        WRITE_DIGITAL_TWIN, SEND_REMINDER, INVOKE_ALL_AGENTS,
    }

    # Resources that are NEVER accessible to any agent (§9 forbidden list).
    FORBIDDEN = {
        "read_user_location",
        "read_payment_data",
        "read_personal_info",
    }


@dataclass
class Role:
    """A role bundles a set of permissions (§9 权限模型)."""

    name: str
    permissions: set[str] = field(default_factory=set)

    def has(self, permission: str) -> bool:
        return permission in self.permissions


# Pre-defined roles (§9 least-privilege).
ROLES: dict[str, Role] = {
    "orchestrator": Role(
        name="orchestrator",
        permissions={
            Permission.READ_VEHICLE_ALL, Permission.WRITE_DIGITAL_TWIN,
            Permission.INVOKE_ALL_AGENTS, Permission.READ_KNOWLEDGE_BASE,
            Permission.SEND_REMINDER, Permission.READ_ALL_AGENT_OUTPUTS,
        },
    ),
    "perception": Role(
        name="perception",
        permissions={Permission.READ_VEHICLE_SENSORS, Permission.READ_VEHICLE_HEALTH},
    ),
    "diagnosis": Role(
        name="diagnosis",
        permissions={Permission.READ_VEHICLE_ALL, Permission.READ_KNOWLEDGE_BASE},
    ),
    "risk_assessment": Role(
        name="risk_assessment",
        permissions={Permission.READ_VEHICLE_ALL, Permission.READ_RISK_HISTORY},
    ),
    "explanation": Role(
        name="explanation",
        permissions={Permission.READ_VEHICLE_ALL},
    ),
    "service_suggestion": Role(
        name="service_suggestion",
        permissions={Permission.READ_VEHICLE_ALL, Permission.WRITE_DIGITAL_TWIN, Permission.SEND_REMINDER},
    ),
    "conflict_resolution": Role(
        name="conflict_resolution",
        permissions={Permission.READ_ALL_AGENT_OUTPUTS},
    ),
    # Expert roles — each scoped to their domain only.
    "动力系统专家": Role(
        name="动力系统专家",
        permissions={Permission.READ_VEHICLE_BATTERY, Permission.READ_VEHICLE_ENGINE},
    ),
    "底盘系统专家": Role(
        name="底盘系统专家",
        permissions={Permission.READ_VEHICLE_BRAKE, Permission.READ_VEHICLE_TIRE},
    ),
    "电气系统专家": Role(
        name="电气系统专家",
        permissions={Permission.READ_VEHICLE_SENSORS, Permission.READ_FAULT_CODES},
    ),
    "驾驶行为专家": Role(
        name="驾驶行为专家",
        permissions={Permission.READ_DRIVING_BEHAVIOR},
    ),
    "保养规划专家": Role(
        name="保养规划专家",
        permissions={Permission.READ_VEHICLE_ALL, Permission.READ_MAINTENANCE_HISTORY},
    ),
    # Extended domain expert roles (§6.5–6.10 of Agent Team Design).
    "车辆价值专家": Role(
        name="车辆价值专家",
        permissions={Permission.READ_VEHICLE_ALL, Permission.READ_MAINTENANCE_HISTORY},
    ),
    "环境适应专家": Role(
        name="环境适应专家",
        permissions={Permission.READ_VEHICLE_SENSORS},
    ),
    "充电智能专家": Role(
        name="充电智能专家",
        permissions={Permission.READ_VEHICLE_BATTERY},
    ),
    "能耗优化专家": Role(
        name="能耗优化专家",
        permissions={Permission.READ_DRIVING_BEHAVIOR, Permission.READ_VEHICLE_ALL},
    ),
    "用户陪伴专家": Role(
        name="用户陪伴专家",
        permissions={Permission.READ_DRIVING_BEHAVIOR},
    ),
}


class PermissionChecker:
    """Enforces the least-privilege principle at runtime.

    Usage:
        if permission_checker.check("battery_expert", "read_vehicle_battery"):
            # proceed
        else:
            logger.warning("Permission denied")
    """

    def __init__(self) -> None:
        self._agent_perms: dict[str, set[str]] = {}

    def register_permissions(self, agent_id: str, permissions: list[str]) -> None:
        """Register the explicit permission list for an agent."""
        # Filter out any forbidden permissions.
        safe = {p for p in permissions if p not in Permission.FORBIDDEN}
        self._agent_perms[agent_id] = safe

    def check(self, agent_id: str, permission: str) -> bool:
        """Return True if *agent_id* is allowed to exercise *permission*."""
        # Forbidden permissions are never granted.
        if permission in Permission.FORBIDDEN:
            logger.warning("Forbidden permission requested: %s by %s", permission, agent_id)
            return False
        perms = self._agent_perms.get(agent_id, set())
        # READ_VEHICLE_ALL implies all read_vehicle_* permissions.
        if Permission.READ_VEHICLE_ALL in perms and permission.startswith("read_vehicle_"):
            return True
        return permission in perms

    def enforce(self, agent_id: str, permission: str, action: Any, *args, **kwargs) -> Any:
        """Execute *action* only if *agent_id* has *permission*.

        Raises PermissionError otherwise.
        """
        if not self.check(agent_id, permission):
            raise PermissionError(
                f"Agent '{agent_id}' lacks permission '{permission}' — "
                f"least-privilege violation blocked."
            )
        return action(*args, **kwargs)

    def audit(self, agent_id: str) -> dict[str, Any]:
        """Return a permission audit report for an agent."""
        perms = self._agent_perms.get(agent_id, set())
        return {
            "agent_id": agent_id,
            "granted": sorted(perms),
            "denied": sorted(Permission.FORBIDDEN),
            "granted_count": len(perms),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialise all agent permissions for API/frontend."""
        return {
            "roles": {name: {"permissions": sorted(r.permissions)} for name, r in ROLES.items()},
            "agents": {
                aid: sorted(perms) for aid, perms in self._agent_perms.items()
            },
        }


# Singleton.
permission_checker = PermissionChecker()
