"""API routers. Each subpackage exposes an `router` (APIRouter)."""
from fastapi import APIRouter

from app.api.agent.router import router as agent_router
from app.api.buy.router import router as buy_router
from app.api.cabin.router import router as cabin_router
from app.api.carsoul.router import router as carsoul_router
from app.api.digital_twin.router import router as digital_twin_router
from app.api.governance.router import router as governance_router
from app.api.health.router import router as health_router
from app.api.knowledge.router import router as knowledge_router
from app.api.map.router import router as map_router
from app.api.orchestrator.router import router as orchestrator_router
from app.api.risk.router import router as risk_router
from app.api.safety.router import router as safety_router
from app.api.timeline.router import router as timeline_router
from app.api.tbox.router import router as tbox_router
from app.api.user.router import router as user_router
from app.api.vehicle.router import router as vehicle_router

api_router = APIRouter(prefix="/api")
api_router.include_router(user_router, prefix="/user", tags=["user"])
api_router.include_router(vehicle_router, prefix="/vehicle", tags=["vehicle"])
api_router.include_router(digital_twin_router, prefix="/digital-twin", tags=["digital-twin"])
api_router.include_router(agent_router, prefix="/agent", tags=["agent"])
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(risk_router, tags=["risk"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(carsoul_router, prefix="/carsoul", tags=["carsoul-world-model"])
api_router.include_router(governance_router, prefix="/governance", tags=["governance"])
api_router.include_router(timeline_router, prefix="/timeline", tags=["timeline"])
api_router.include_router(safety_router, prefix="/safety", tags=["safety-compliance"])
api_router.include_router(map_router, prefix="/map", tags=["map"])
api_router.include_router(buy_router, prefix="/buy", tags=["buy-advisor"])
api_router.include_router(cabin_router, prefix="/cabin", tags=["cabin-companion"])
# T-BOX 适配层：挂载在 /api/v1/tbox（C-11 版本前缀），车况中心只读遥测展示。
api_router.include_router(tbox_router, prefix="/v1/tbox", tags=["tbox-adapter"])
# Orchestrator 总控调度：挂载在 /api/v1/orchestrator（C-11 版本前缀），
# 端点 POST /dispatch + GET /agents（SPEC §5.1 #1/#2）。
api_router.include_router(orchestrator_router, prefix="/v1/orchestrator",
                          tags=["orchestrator"])

__all__ = ["api_router"]
