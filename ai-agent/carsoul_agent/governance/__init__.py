"""CarSoul Agent Governance Layer — 智能体治理控制层.

This package implements the governance architecture described in
《CarSoul Agent Governance Architecture V1.0》:

    ┌───────────────────────────────────────┐
    │        Agent Governance Layer          │
    │  (registry · permissions · lifecycle)  │
    └───────────────────────────────────────┘
                      ↓
    ┌───────────────────────────────────────┐
    │          Judge Agent                   │
    │  (conflict resolution · fusion)        │
    └───────────────────────────────────────┘
                      ↓
    ┌───────────────────────────────────────┐
    │     Skill / MCP / Workflow Perms       │
    │  (resource governance · sandbox)       │
    └───────────────────────────────────────┘
                      ↓
    ┌───────────────────────────────────────┐
    │       Version Manager                   │
    │  (canary / stable / deprecated)        │
    └───────────────────────────────────────┘

Modules:
  - registry:              Enhanced Agent Registry with metadata, state, version
  - permissions:           Role-based permission model (Agent → Role → Permission → Data)
  - judge:                 Judge Agent for multi-agent conflict resolution
  - lifecycle:             Agent lifecycle state machine (ACTIVE/BUSY/ERROR/OFFLINE)
  - skill_registry:        Skill Registry — skills as first-class registered entities
  - mcp_registry:          MCP Registry — vehicle capability interface registration
  - workflow_permissions:  Workflow-level permission control (per-workflow agent/skill/data)
  - sandbox:               Sandbox executor — safe execution environment
  - version_manager:       Agent version management (canary → stable rollout)
"""
from carsoul_agent.governance.registry import (
    AgentMetadata,
    AgentState,
    ManagedAgentRegistry,
    managed_registry,
    register_governance_agents,
)
from carsoul_agent.governance.permissions import (
    Permission,
    PermissionChecker,
    Role,
    permission_checker,
)
from carsoul_agent.governance.judge import JudgeAgent
from carsoul_agent.governance.lifecycle import AgentLifecycleManager, lifecycle_manager
from carsoul_agent.governance.skill_registry import (
    SkillMetadata,
    SkillRegistry,
    skill_registry,
    register_governance_skills,
)
from carsoul_agent.governance.mcp_registry import (
    MCPInterface,
    MCPRegistry,
    mcp_registry,
    register_mcp_interfaces,
)
from carsoul_agent.governance.workflow_permissions import (
    WorkflowPermission,
    WorkflowPermissionChecker,
    workflow_permission_checker,
    register_workflow_permissions,
)
from carsoul_agent.governance.sandbox import (
    SandboxConfig,
    SandboxExecutor,
    sandbox_executor,
)
from carsoul_agent.governance.version_manager import (
    AgentVersion,
    VersionManager,
    VersionStatus,
    version_manager,
    register_agent_versions,
)

__all__ = [
    # Registry
    "AgentMetadata",
    "AgentState",
    "ManagedAgentRegistry",
    "managed_registry",
    "register_governance_agents",
    # Permissions
    "Permission",
    "PermissionChecker",
    "Role",
    "permission_checker",
    # Judge
    "JudgeAgent",
    # Lifecycle
    "AgentLifecycleManager",
    "lifecycle_manager",
    # Skill Registry
    "SkillMetadata",
    "SkillRegistry",
    "skill_registry",
    "register_governance_skills",
    # MCP Registry
    "MCPInterface",
    "MCPRegistry",
    "mcp_registry",
    "register_mcp_interfaces",
    # Workflow Permissions
    "WorkflowPermission",
    "WorkflowPermissionChecker",
    "workflow_permission_checker",
    "register_workflow_permissions",
    # Sandbox
    "SandboxConfig",
    "SandboxExecutor",
    "sandbox_executor",
    # Version Manager
    "AgentVersion",
    "VersionManager",
    "VersionStatus",
    "version_manager",
    "register_agent_versions",
]
