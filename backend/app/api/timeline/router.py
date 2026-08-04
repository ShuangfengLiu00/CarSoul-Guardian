"""Timeline Demo API — 'A Car's Life' narrative endpoint.

GET /api/timeline/life-story
    Returns the complete 3-year life story of a virtual vehicle,
    including telemetry, memories, agent collaboration, and a
    traceable health report. Always returns demo_mode=True.
"""
from fastapi import APIRouter

from app.schemas.timeline import LifeStoryResponse
from app.services.timeline_service import generate_life_story

router = APIRouter()


@router.get("/life-story", response_model=LifeStoryResponse)
def life_story() -> LifeStoryResponse:
    """Return the complete 'A Car's Life' narrative.

    This endpoint generates a deterministic 3-year timeline:
    2025 (birth) → 2026 (usage) → 2027 (anomaly).

    Every number in the health report is traceable to a memory entry,
    telemetry snapshot, or agent finding via the `traceable_items` list.
    """
    return generate_life_story()
