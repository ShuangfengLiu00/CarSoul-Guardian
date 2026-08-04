"""API routers. Each subpackage exposes an `router` (APIRouter)."""
from fastapi import APIRouter

from app.api.agent.router import router as agent_router
from app.api.digital_twin.router import router as digital_twin_router
from app.api.governance.router import router as governance_router
from app.api.health.router import router as health_router
from app.api.knowledge.router import router as knowledge_router
from app.api.risk.router import router as risk_router
from app.api.timeline.router import router as timeline_router
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
api_router.include_router(governance_router, prefix="/governance", tags=["governance"])
api_router.include_router(timeline_router, prefix="/timeline", tags=["timeline"])

__all__ = ["api_router"]
