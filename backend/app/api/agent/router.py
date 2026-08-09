"""Agent API: chat endpoint.

IMPORTANT (architecture rule): this route NEVER calls an LLM directly. It
delegates to `app.services.agent_service`, which in turn talks to the
`carsoul_agent` package. This keeps the agent layer swappable and
multi-agent-ready.
"""
from fastapi import APIRouter

from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.services import agent_service

router = APIRouter()


@router.post("/chat", response_model=AgentChatResponse)
async def chat(payload: AgentChatRequest) -> AgentChatResponse:
    result = await agent_service.chat(
        user=payload.user,
        message=payload.message,
        session_id=payload.session_id,
    )
    return AgentChatResponse(**result)
