"""Governance & Workflow Engine API.

Exposes the Agent Governance Layer and Workflow Engine state for
frontend visualisation:

  - Agent Registry (metadata, capabilities, version, state)
  - Permission model (per-agent permissions)
  - Agent fleet health (active/busy/error/offline counts)
  - Judge Agent info
  - Recent workflow execution memories
  - Lifecycle event log
  - Skill Registry (35 skills with I/O schemas)
  - MCP Registry (15 vehicle capability interfaces)
  - Workflow Permissions (per-workflow agent/skill/data access)
  - Sandbox config and status
  - Agent Version Manager (canary/stable rollout)
  - AgentLoop Observation Layer (trace, evaluation, optimization, evolution)
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


def _get_registry():
    """Lazy-load the governance registry (avoids import at module level)."""
    from carsoul_agent.governance import managed_registry, register_governance_agents
    if not managed_registry.names():
        register_governance_agents()
    return managed_registry


def _get_permission_checker():
    from carsoul_agent.governance import permission_checker, register_governance_agents
    if not permission_checker._agent_perms:
        register_governance_agents()
        for meta in _get_registry().all_metadata():
            permission_checker.register_permissions(meta.agent_id, meta.permissions)
    return permission_checker


def _get_lifecycle_manager():
    from carsoul_agent.governance import lifecycle_manager
    return lifecycle_manager


# ------------------------------------------------------------------ #
#  Existing endpoints
# ------------------------------------------------------------------ #
@router.get("/agents", summary="List all registered agents")
def list_agents() -> dict:
    """Return all agents in the governance registry with full metadata."""
    return _get_registry().to_dict()


@router.get("/agents/{agent_id}", summary="Get a specific agent's details")
def get_agent(agent_id: str) -> dict:
    meta = _get_registry().get(agent_id)
    if meta is None:
        return {"error": f"Agent '{agent_id}' not found", "agent_id": agent_id}
    return meta.to_dict()


@router.get("/permissions", summary="List all agent permissions")
def list_permissions() -> dict:
    return _get_permission_checker().to_dict()


@router.get("/permissions/{agent_id}", summary="Audit a single agent's permissions")
def audit_permissions(agent_id: str) -> dict:
    return _get_permission_checker().audit(agent_id)


@router.get("/health", summary="Agent fleet health summary")
def fleet_health() -> dict:
    return _get_lifecycle_manager().health_summary()


@router.get("/lifecycle/events", summary="Recent lifecycle events")
def lifecycle_events(limit: int = 50) -> dict:
    return {"events": _get_lifecycle_manager().event_log(limit=limit)}


@router.get("/judge", summary="Judge Agent info")
def judge_info() -> dict:
    from carsoul_agent.governance import JudgeAgent
    return JudgeAgent().to_dict()


@router.get("/workflows", summary="Recent workflow execution memories")
def recent_workflows(limit: int = 10) -> dict:
    from carsoul_agent.workflow_engine.memory import get_recent_memories
    return {"workflows": get_recent_memories(limit=limit)}


@router.get("/overview", summary="Governance overview dashboard")
def governance_overview() -> dict:
    registry = _get_registry()
    lifecycle = _get_lifecycle_manager()
    return {
        "registry": {
            "agent_count": len(registry.names()),
            "active_count": len(registry.list_active()),
        },
        "fleet_health": lifecycle.health_summary(),
        "agents": [m.to_dict() for m in registry.all_metadata()],
    }


# ------------------------------------------------------------------ #
#  Skill Registry endpoints
# ------------------------------------------------------------------ #
def _get_skill_registry():
    from carsoul_agent.governance import skill_registry, register_governance_skills
    if not skill_registry.all_skills():
        register_governance_skills()
    return skill_registry


@router.get("/skills", summary="List all registered skills")
def list_skills() -> dict:
    return _get_skill_registry().to_dict()


@router.get("/skills/{skill_id}", summary="Get a specific skill's details")
def get_skill(skill_id: str) -> dict:
    skill = _get_skill_registry().get(skill_id)
    if skill is None:
        return {"error": f"Skill '{skill_id}' not found", "skill_id": skill_id}
    return skill.to_dict()


@router.get("/skills/agent/{agent_id}", summary="List skills by agent")
def skills_by_agent(agent_id: str) -> dict:
    skills = _get_skill_registry().find_by_agent(agent_id)
    return {"agent_id": agent_id, "skills": [s.to_dict() for s in skills]}


# ------------------------------------------------------------------ #
#  MCP Registry endpoints
# ------------------------------------------------------------------ #
def _get_mcp_registry():
    from carsoul_agent.governance import mcp_registry, register_mcp_interfaces
    if not mcp_registry.all_interfaces():
        register_mcp_interfaces()
    return mcp_registry


@router.get("/mcp", summary="List all MCP interfaces")
def list_mcp() -> dict:
    return _get_mcp_registry().to_dict()


@router.get("/mcp/{interface_id}", summary="Get a specific MCP interface")
def get_mcp(interface_id: str) -> dict:
    iface = _get_mcp_registry().get(interface_id)
    if iface is None:
        return {"error": f"MCP interface '{interface_id}' not found"}
    return iface.to_dict()


# ------------------------------------------------------------------ #
#  Workflow Permissions endpoints
# ------------------------------------------------------------------ #
def _get_workflow_perms():
    from carsoul_agent.governance import (
        workflow_permission_checker,
        register_workflow_permissions,
    )
    if not workflow_permission_checker.all_permissions():
        register_workflow_permissions()
    return workflow_permission_checker


@router.get("/workflow-permissions", summary="List all workflow permissions")
def list_workflow_permissions() -> dict:
    return _get_workflow_perms().to_dict()


@router.get("/workflow-permissions/{workflow_name}", summary="Get workflow permission details")
def get_workflow_permission(workflow_name: str) -> dict:
    perm = _get_workflow_perms().get(workflow_name)
    if perm is None:
        return {"error": f"Workflow '{workflow_name}' not found"}
    return perm.to_dict()


# ------------------------------------------------------------------ #
#  Sandbox endpoints
# ------------------------------------------------------------------ #
@router.get("/sandbox", summary="Sandbox configuration and status")
def sandbox_status() -> dict:
    from carsoul_agent.governance import sandbox_executor
    return sandbox_executor.to_dict()


# ------------------------------------------------------------------ #
#  Version Manager endpoints
# ------------------------------------------------------------------ #
def _get_version_manager():
    from carsoul_agent.governance import version_manager, register_agent_versions
    if not version_manager.all_versions():
        register_agent_versions()
    return version_manager


@router.get("/versions", summary="List all agent versions")
def list_versions() -> dict:
    return _get_version_manager().to_dict()


@router.get("/versions/{agent_id}", summary="Get version history for an agent")
def agent_versions(agent_id: str) -> dict:
    mgr = _get_version_manager()
    history = mgr.get_history(agent_id)
    current = mgr.get_current(agent_id)
    return {
        "agent_id": agent_id,
        "current": current.to_dict() if current else None,
        "history": [v.to_dict() for v in history],
    }


class PromoteVersionRequest(BaseModel):
    agent_id: str
    version: str
    canary_percentage: int = 10


@router.post("/versions/promote-canary", summary="Promote a version to canary")
def promote_canary(req: PromoteVersionRequest) -> dict:
    success = _get_version_manager().promote_to_canary(
        req.agent_id, req.version, req.canary_percentage
    )
    return {"success": success, "agent_id": req.agent_id, "version": req.version}


@router.post("/versions/promote-stable", summary="Promote a version to stable")
def promote_stable(req: PromoteVersionRequest) -> dict:
    success = _get_version_manager().promote_to_stable(req.agent_id, req.version)
    return {"success": success, "agent_id": req.agent_id, "version": req.version}


# ------------------------------------------------------------------ #
#  AgentLoop Observation Layer endpoints
# ------------------------------------------------------------------ #
@router.get("/observation/traces", summary="Recent execution traces")
def recent_traces(limit: int = 20) -> dict:
    from carsoul_agent.observation import trace_collector
    return {"traces": trace_collector.get_recent_traces(limit=limit)}


@router.get("/observation/traces/{trace_id}", summary="Get a specific trace")
def get_trace(trace_id: str) -> dict:
    from carsoul_agent.observation import trace_collector
    trace = trace_collector.get_trace(trace_id)
    if trace is None:
        return {"error": f"Trace '{trace_id}' not found"}
    return trace


@router.get("/observation/token-stats", summary="Token consumption statistics")
def token_stats() -> dict:
    from carsoul_agent.observation import trace_collector
    return trace_collector.get_token_stats()


@router.get("/observation/evaluation", summary="Agent evaluation summary")
def evaluation_summary() -> dict:
    from carsoul_agent.observation import evaluation_engine
    return evaluation_engine.get_fleet_evaluation()


@router.get("/observation/evaluation/{agent_id}", summary="Agent-specific evaluations")
def agent_evaluation(agent_id: str, limit: int = 50) -> dict:
    from carsoul_agent.observation import evaluation_engine
    return {
        "agent_id": agent_id,
        "evaluations": evaluation_engine.get_agent_evaluations(agent_id, limit=limit),
    }


class UserFeedbackRequest(BaseModel):
    workflow_id: str
    feedback: str
    rating: int = 5


@router.post("/observation/feedback", summary="Submit user feedback")
def submit_feedback(req: UserFeedbackRequest) -> dict:
    from carsoul_agent.observation import evaluation_engine
    evaluation_engine.record_user_feedback(req.workflow_id, req.feedback, req.rating)
    return {"success": True, "workflow_id": req.workflow_id}


@router.get("/observation/optimizations", summary="Pending optimization actions")
def pending_optimizations() -> dict:
    from carsoul_agent.observation import optimization_loop
    return {"optimizations": optimization_loop.get_pending_optimizations()}


@router.post("/observation/optimizations/run", summary="Run optimization cycle")
def run_optimization_cycle() -> dict:
    from carsoul_agent.observation import optimization_loop
    actions = optimization_loop.run_cycle()
    return {"generated_actions": len(actions), "actions": [a.to_dict() for a in actions]}


class ApplyOptimizationRequest(BaseModel):
    action_id: str


@router.post("/observation/optimizations/apply", summary="Apply an optimization action")
def apply_optimization(req: ApplyOptimizationRequest) -> dict:
    from carsoul_agent.observation import optimization_loop
    success = optimization_loop.apply_optimization(req.action_id)
    return {"success": success, "action_id": req.action_id}


@router.get("/observation/evolution", summary="Agent evolution summary")
def evolution_summary() -> dict:
    from carsoul_agent.observation import evolution_manager
    return evolution_manager.get_evolution_summary()


@router.get("/observation/evolution/{agent_id}", summary="Agent evolution history")
def agent_evolution(agent_id: str) -> dict:
    from carsoul_agent.observation import evolution_manager
    return {
        "agent_id": agent_id,
        "evolution_history": evolution_manager.get_agent_evolution_history(agent_id),
    }


# ------------------------------------------------------------------ #
#  Evolution Engine endpoints (Agent Evolution Engine V1.0)
# ------------------------------------------------------------------ #
@router.get("/evolution/dashboard", summary="Evolution Engine dashboard")
def evolution_dashboard() -> dict:
    """返回进化引擎仪表盘数据 — 聚合所有进化子引擎状态."""
    from carsoul_agent.observation import evolution_engine
    return evolution_engine.get_dashboard()


@router.post("/evolution/run-cycle", summary="Run a full evolution cycle")
def run_evolution_cycle() -> dict:
    """执行一次完整的进化闭环（评估→反思→经验→技能进化→优化→里程碑）."""
    from carsoul_agent.observation import evolution_engine
    result = evolution_engine.run_evolution_cycle()
    return result.to_dict()


@router.get("/evolution/cycles", summary="Evolution cycle history")
def evolution_cycles(limit: int = 20) -> dict:
    """返回进化周期执行历史."""
    from carsoul_agent.observation import evolution_engine
    return {"cycles": evolution_engine.get_cycle_history(limit=limit)}


@router.post("/evolution/seed-demo", summary="Seed demo data for evolution engine")
def seed_evolution_demo() -> dict:
    """注入演示数据，展示进化引擎效果（冬季电池诊断场景）."""
    from carsoul_agent.observation import evolution_engine
    return evolution_engine.seed_demo_data()


class TaskCompletedRequest(BaseModel):
    task_id: str
    agent_id: str
    task_type: str
    problem: str
    solution: str = ""
    result: str = ""
    task_success: bool = True
    user_satisfied: bool = True
    prediction_accurate: bool = True
    vehicle_id: str = ""
    missing_data: list[str] = []
    reasoning_errors: list[str] = []


@router.post("/evolution/task-completed", summary="Trigger evolution hook after task completion")
def task_completed_hook(req: TaskCompletedRequest) -> dict:
    """任务完成后触发进化钩子 — 自动评估、反思、经验提取、记忆存储."""
    from carsoul_agent.observation import evolution_engine
    return evolution_engine.on_task_completed(
        task_id=req.task_id,
        agent_id=req.agent_id,
        task_type=req.task_type,
        problem=req.problem,
        solution=req.solution,
        result=req.result,
        task_success=req.task_success,
        user_satisfied=req.user_satisfied,
        prediction_accurate=req.prediction_accurate,
        vehicle_id=req.vehicle_id,
        missing_data=req.missing_data,
        reasoning_errors=req.reasoning_errors,
    )


# --- Experience Miner ---
@router.get("/evolution/experience", summary="Experience mining summary")
def experience_summary() -> dict:
    """返回经验挖掘引擎摘要（案例数、模式数、置信度）."""
    from carsoul_agent.observation import experience_miner
    return experience_miner.get_summary()


@router.get("/evolution/experience/cases", summary="All experience cases")
def experience_cases(limit: int = 100) -> dict:
    """返回所有经验案例."""
    from carsoul_agent.observation import experience_miner
    return {"cases": experience_miner.get_all_cases(limit=limit)}


@router.get("/evolution/experience/patterns", summary="Discovered experience patterns")
def experience_patterns() -> dict:
    """返回所有已发现的经验模式."""
    from carsoul_agent.observation import experience_miner
    return {"patterns": experience_miner.get_all_patterns()}


@router.get("/evolution/experience/search", summary="Search similar experiences")
def search_experience(
    task_type: str,
    problem: str = "",
    limit: int = 5,
) -> dict:
    """检索相似经验案例和模式."""
    from carsoul_agent.observation import experience_miner
    return {
        "task_type": task_type,
        "problem": problem,
        "results": experience_miner.retrieve_similar(
            task_type=task_type, problem=problem, limit=limit
        ),
    }


# --- Reflection Engine ---
@router.get("/evolution/reflection", summary="Reflection engine summary")
def reflection_summary() -> dict:
    """返回反思引擎摘要."""
    from carsoul_agent.observation import reflection_engine
    return reflection_engine.get_summary()


@router.get("/evolution/reflection/recent", summary="Recent reflection reports")
def recent_reflections(limit: int = 20) -> dict:
    """返回最近的反思报告."""
    from carsoul_agent.observation import reflection_engine
    return {"reflections": reflection_engine.get_recent_reflections(limit=limit)}


@router.get("/evolution/reflection/{agent_id}", summary="Agent reflection history")
def agent_reflections(agent_id: str, limit: int = 50) -> dict:
    """返回某 Agent 的反思历史和弱点分析."""
    from carsoul_agent.observation import reflection_engine
    return {
        "agent_id": agent_id,
        "reflections": reflection_engine.get_agent_reflections(agent_id, limit=limit),
        "weaknesses": reflection_engine.get_agent_weaknesses(agent_id),
    }


# --- Skill Evolution Engine ---
@router.get("/evolution/skill", summary="Skill evolution summary")
def skill_evolution_summary() -> dict:
    """返回技能进化引擎摘要."""
    from carsoul_agent.observation import skill_evolution_engine
    return skill_evolution_engine.get_summary()


@router.get("/evolution/skill/versions/{skill_id}", summary="Skill version history")
def skill_versions(skill_id: str) -> dict:
    """返回某技能的完整版本历史."""
    from carsoul_agent.observation import skill_evolution_engine
    return {
        "skill_id": skill_id,
        "versions": skill_evolution_engine.get_skill_versions(skill_id),
    }


@router.get("/evolution/skill/proposals", summary="Skill mutation proposals")
def skill_proposals(limit: int = 50) -> dict:
    """返回所有技能变异提案."""
    from carsoul_agent.observation import skill_evolution_engine
    return {"proposals": skill_evolution_engine.get_all_proposals(limit=limit)}


@router.get("/evolution/skill/proposals/pending", summary="Pending skill mutation proposals")
def pending_skill_proposals() -> dict:
    """返回待处理的技能变异提案."""
    from carsoul_agent.observation import skill_evolution_engine
    return {"proposals": skill_evolution_engine.get_pending_proposals()}


@router.post("/evolution/skill/auto-evolve/{skill_id}", summary="Auto-evolve a skill")
def auto_evolve_skill(skill_id: str) -> dict:
    """自动检测并触发技能进化（检测→提案→治理审批→部署）."""
    from carsoul_agent.observation import skill_evolution_engine
    return skill_evolution_engine.auto_evolve_skill(skill_id)


class RunApprovalRequest(BaseModel):
    proposal_id: str


@router.post("/evolution/skill/approve", summary="Run approval pipeline for a mutation proposal")
def run_approval_pipeline(req: RunApprovalRequest) -> dict:
    """执行技能变异提案的治理审批流程（测试→沙箱→评分→批准→上线）."""
    from carsoul_agent.observation import skill_evolution_engine
    return skill_evolution_engine.run_approval_pipeline(req.proposal_id)


# --- Evolution Memory ---
@router.get("/evolution/memory/timeline", summary="Evolution timeline")
def evolution_timeline(limit: int = 50) -> dict:
    """返回全局进化时间线."""
    from carsoul_agent.memory.evolution_memory import evolution_memory
    return {"timeline": evolution_memory.get_evolution_timeline(limit=limit)}


@router.get("/evolution/memory/{agent_id}", summary="Agent growth trajectory")
def agent_growth(agent_id: str) -> dict:
    """返回某 Agent 的成长轨迹."""
    from carsoul_agent.memory.evolution_memory import evolution_memory
    return {
        "agent_id": agent_id,
        "milestones": evolution_memory.get_agent_milestones(agent_id),
        "growth": evolution_memory.get_agent_growth(agent_id),
    }


# ------------------------------------------------------------------ #
#  Comprehensive overview
# ------------------------------------------------------------------ #
@router.get("/full-overview", summary="Complete governance overview")
def full_overview() -> dict:
    registry = _get_registry()
    lifecycle = _get_lifecycle_manager()
    skill_reg = _get_skill_registry()
    mcp_reg = _get_mcp_registry()
    wf_perms = _get_workflow_perms()
    ver_mgr = _get_version_manager()
    return {
        "registry": {
            "agent_count": len(registry.names()),
            "active_count": len(registry.list_active()),
        },
        "fleet_health": lifecycle.health_summary(),
        "skills": {
            "total_skills": len(skill_reg.all_skills()),
            "categories": list({s.category for s in skill_reg.all_skills()}),
        },
        "mcp": {
            "total_interfaces": len(mcp_reg.all_interfaces()),
            "categories": list({i.category for i in mcp_reg.all_interfaces()}),
        },
        "workflow_permissions": {
            "total_workflows": len(wf_perms.all_permissions()),
        },
        "versions": {
            "total_versions": len(ver_mgr.all_versions()),
        },
        "agents": [m.to_dict() for m in registry.all_metadata()],
    }
