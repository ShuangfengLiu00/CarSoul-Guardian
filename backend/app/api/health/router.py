"""Health API: dashboard overview data."""
from fastapi import APIRouter

from app.schemas.health import AlertItem, HealthOverview

router = APIRouter()


@router.get("/overview", response_model=HealthOverview)
def overview() -> HealthOverview:
    # TASK006 returns illustrative data; TASK007 computes it from the
    # vehicle digital-life archive + health records.
    return HealthOverview(
        health_score=92,
        agent_status="active",
        recent_alerts=[
            AlertItem(level="warning", title="保养临近",
                      detail="Model Y 距下次机油保养约 1,200 km"),
            AlertItem(level="info", title="胎压正常",
                      detail="四轮胎压均在标准区间"),
            AlertItem(level="info", title="驾驶行为良好",
                      detail="本周急加速/急刹车次数低于均值"),
        ],
    )
