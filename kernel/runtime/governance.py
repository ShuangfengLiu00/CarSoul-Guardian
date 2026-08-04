"""Governance profiles for the Runtime SDK.

The governance layer enforces the "守护非控制" (guard-not-control)
principle at the SDK level.  A :class:`GovernanceProfile` configures
what an agent created via ``create_agent`` is allowed to do.

Default profile
---------------
The default profile is **read-only**: only read tools from the
existing tool registry are whitelisted.  Write tools (push_reminder,
record_lifecycle_event, write_service_suggestion, create_service_order)
are blocked unless the caller explicitly sets ``read_only=False``.

This means governance constraints are enforced *by default* — the
acceptance criterion "治理约束经 SDK 默认生效（只读工具白名单）"
is satisfied out of the box.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ------------------------------------------------------------------ #
#  Tool classification
# ------------------------------------------------------------------ #

# Read-only tools — safe for any agent to call.
READ_TOOLS: frozenset[str] = frozenset({
    "get_vehicle_info",
    "get_health_score",
    "get_maintenance_plan",
    "get_driving_behavior",
    "get_lifecycle_timeline",
    "get_alerts",
    "get_calibration_context",
    "search_knowledge_base",
    "knowledge_base_stats",
})

# Write tools — guarded, require explicit permission.
WRITE_TOOLS: frozenset[str] = frozenset({
    "push_reminder",
    "record_lifecycle_event",
    "write_service_suggestion",
    "create_service_order",
})

# Permanently forbidden tools — no agent may ever use these.
FORBIDDEN_TOOLS: frozenset[str] = frozenset({
    "control_actuator",
    "control_steering",
    "control_brake",
    "control_throttle",
    "read_user_location",
    "read_payment_data",
    "read_personal_info",
})


@dataclass
class GovernanceProfile:
    """Configuration that governs what an SDK-created agent may do.

    Attributes
    ----------
    read_only : bool
        If ``True`` (default), only read tools are whitelisted.
        Write tools are blocked.  Set to ``False`` to allow guarded
        write tools.
    allowed_tools : list[str] | None
        Explicit whitelist.  If provided, *only* these tools are
        allowed (intersected with the read_only / forbidden rules).
        If ``None``, the default whitelist applies.
    forbidden_tools : list[str]
        Additional tools to block (merged with FORBIDDEN_TOOLS).
    max_execution_time : int
        Maximum tool execution time in seconds.
    network_access : bool
        Whether tools may make network calls.
    file_write_access : bool
        Whether tools may write to the filesystem.
    """

    read_only: bool = True
    allowed_tools: list[str] | None = None
    forbidden_tools: list[str] = field(default_factory=list)
    max_execution_time: int = 30
    network_access: bool = False
    file_write_access: bool = False

    def effective_allowed(self) -> frozenset[str]:
        """Compute the effective tool whitelist.

        The result is the intersection of:
        1. The read-only whitelist (if read_only=True) or read+write
        2. The explicit allowed_tools (if provided)
        3. Minus the forbidden set
        """
        if self.read_only:
            base = READ_TOOLS
        else:
            base = READ_TOOLS | WRITE_TOOLS

        if self.allowed_tools is not None:
            base = base & frozenset(self.allowed_tools)

        forbidden = FORBIDDEN_TOOLS | frozenset(self.forbidden_tools)
        return base - forbidden

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check whether a tool is allowed under this profile."""
        return tool_name in self.effective_allowed()

    def validate_tool(self, tool_name: str) -> tuple[bool, str]:
        """Validate a tool call, returning (allowed, reason).

        Returns
        -------
        (bool, str)
            ``(True, "")`` if allowed; ``(False, reason)`` if blocked.
        """
        if tool_name in FORBIDDEN_TOOLS:
            return False, f"工具 '{tool_name}' 被永久禁止"
        if tool_name in frozenset(self.forbidden_tools):
            return False, f"工具 '{tool_name}' 被当前治理配置禁止"
        if self.read_only and tool_name in WRITE_TOOLS:
            return False, (
                f"工具 '{tool_name}' 是写操作，当前治理配置为只读模式"
            )
        if self.allowed_tools is not None and tool_name not in self.allowed_tools:
            return False, f"工具 '{tool_name}' 不在白名单中"
        if not self.is_tool_allowed(tool_name):
            return False, f"工具 '{tool_name}' 不被允许"
        return True, ""

    def to_dict(self) -> dict[str, Any]:
        """Serialise for logging / debugging."""
        return {
            "read_only": self.read_only,
            "effective_allowed": sorted(self.effective_allowed()),
            "forbidden": sorted(FORBIDDEN_TOOLS | frozenset(self.forbidden_tools)),
            "max_execution_time": self.max_execution_time,
            "network_access": self.network_access,
            "file_write_access": self.file_write_access,
        }
