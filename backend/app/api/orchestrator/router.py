"""Orchestrator API: dispatch endpoint + agent registry listing.

Architecture rule: this router only delegates to app.orchestrator.dispatcher.
It never calls an LLM or carModel directly.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.orchestrator.dispatcher import Orchestrator
from app.orchestrator.routing_table import ROUTING_TABLE

router = APIRouter()


class DispatchRequest(BaseModel):
    user_message: str
    user_id: str = "anonymous"
    vehicle_id: str = ""


class DispatchResponse(BaseModel):
    result: dict
    agents_involved: list[str]
    dispatch_log_id: str
    execution_mode: str


_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """单例 Orchestrator。Agent 在此注册（其他 teammate 实现后接入）。"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(_build_agents())
    return _orchestrator


def _build_agents() -> dict:
    """注册可用垂直 Agent（T3：3 个 MVP 垂直 Agent 已实装）。

    仅注册 routing_table 中 enabled=True 且已实现的 agent；
    未实现的（阶段 2：insurance_risk / used_car_valuation）保持不注册，
    由 dispatcher 走 DISABLED_AGENT_REPLY 兜底。
    """
    agents: dict = {}
    # T3 实装：3 个 MVP 垂直 Agent（battery_health / driving_safety / charging_optimization）
    from app.agents.battery_health_agent import BatteryHealthAgent
    from app.agents.charging_optimization_agent import ChargingOptimizationAgent
    from app.agents.driving_safety_agent import DrivingSafetyAgent

    agents["battery_health"] = BatteryHealthAgent()
    agents["driving_safety"] = DrivingSafetyAgent()
    agents["charging_optimization"] = ChargingOptimizationAgent()
    return agents


@router.post("/dispatch", response_model=DispatchResponse)
def dispatch(req: DispatchRequest) -> DispatchResponse:
    res = get_orchestrator().dispatch(
        req.user_message, req.user_id,
        vehicle_id=req.vehicle_id or None)
    return DispatchResponse(
        result={"answer": res.answer, "status": res.status,
                "caveats": res.caveats, "sub_results": res.sub_results,
                "confidence": res.confidence},
        agents_involved=res.agents_involved,
        dispatch_log_id=res.dispatch_log_id,
        execution_mode=res.execution_mode,
    )


@router.get("/agents")
def list_agents() -> dict:
    orch = get_orchestrator()
    agents = []
    for name, cfg in ROUTING_TABLE.items():
        agents.append({
            "agent_name": cfg["agent_name"],
            "enabled": cfg["enabled"],
            "description": cfg["description"],
            "registered": name in orch.registered_agents,
        })
    return {"agents": agents, "total": len(agents)}
