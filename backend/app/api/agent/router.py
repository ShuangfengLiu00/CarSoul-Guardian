"""Agent API: chat endpoint.

IMPORTANT (architecture rule): this route NEVER calls an LLM directly. It
delegates to `app.services.agent_service`, which in turn talks to the
`carsoul_agent` package. This keeps the agent layer swappable and
multi-agent-ready.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.services import agent_service, vehicle_service
from app.services.vehicle_mapping import resolve_carsoul_id

router = APIRouter()


@router.post("/chat", response_model=AgentChatResponse)
async def chat(
    payload: AgentChatRequest,
    db: Session = Depends(get_db),
) -> AgentChatResponse:
    # 品牌精确映射：Guardian 整数 id → carModel CSxxx（按 brand/model 语义匹配，
    # 不再用偏移锚定张冠李戴）。映射缺失时回退偏移锚定，全无本车时回退全局默认车。
    vehicle = None
    if payload.vehicle_id is not None:
        vehicle = vehicle_service.get_vehicle(db, payload.vehicle_id)
    carsoul_id = resolve_carsoul_id(
        vehicle, default=settings.CARSOUL_WORLD_DEFAULT_VEHICLE_ID
    )
    result = await agent_service.chat(
        user=payload.user,
        message=payload.message,
        session_id=payload.session_id,
        vehicle_id=carsoul_id,
    )
    return AgentChatResponse(**result)
