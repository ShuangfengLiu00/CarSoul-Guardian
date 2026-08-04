"""Tool calling layer.

Two tiers of tools:
  - **Read tools** (vehicle_tools): query vehicle archive data (health,
    maintenance, driving behavior, lifecycle, alerts).
  - **Guarded write tools** (guard_tools): the *only* write-capable tools.
    Limited to push_reminder / record_lifecycle_event / write_service_suggestion.
    No actuator-control tools exist — this is the tool-layer gate.
"""
from carsoul_agent.tools.base import BaseTool, ToolRegistry, ToolResult, default_registry
from carsoul_agent.tools.vehicle_tools import (
    GetAlertsTool,
    GetDrivingBehaviorTool,
    GetHealthScoreTool,
    GetLifecycleTimelineTool,
    GetMaintenancePlanTool,
    GetVehicleInfoTool,
)
from carsoul_agent.tools.guard_tools import (
    ActionStore,
    PushReminderTool,
    RecordLifecycleEventTool,
    WriteServiceSuggestionTool,
    action_store,
)
from carsoul_agent.tools.knowledge_tool import (
    KnowledgeBaseStatsTool,
    SearchKnowledgeBaseTool,
)

__all__ = [
    # Base
    "BaseTool",
    "ToolRegistry",
    "ToolResult",
    "default_registry",
    # Read tools
    "GetVehicleInfoTool",
    "GetHealthScoreTool",
    "GetMaintenancePlanTool",
    "GetDrivingBehaviorTool",
    "GetLifecycleTimelineTool",
    "GetAlertsTool",
    # Knowledge tools (RAG)
    "SearchKnowledgeBaseTool",
    "KnowledgeBaseStatsTool",
    # Guarded write tools
    "PushReminderTool",
    "RecordLifecycleEventTool",
    "WriteServiceSuggestionTool",
    "ActionStore",
    "action_store",
]
