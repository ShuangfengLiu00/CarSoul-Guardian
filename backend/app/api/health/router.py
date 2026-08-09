"""Health API: dashboard overview data."""
from fastapi import APIRouter

from app.schemas.health import AlertItem, HealthOverview
from app.services import agent_service

router = APIRouter()


@router.get("/overview", response_model=HealthOverview)
def overview() -> HealthOverview:
    # TASK006 returns illustrative data; TASK007 computes it from the
    # vehicle digital-life archive + health records.
    #
    # agent_status 曾硬编码 "active" —— 这是 Dashboard 死绿灯的真正源头：
    # 前端读的就是这个字段。现改为如实上报**最近一次真实观测到**的大模型
    # 链路状态；在任何一轮对话真正发生之前为 "unknown"（未观测即不表态）。
    return HealthOverview(
        health_score=92,
        agent_status=agent_service.get_last_link_state()["agent_status"],
        recent_alerts=[
            AlertItem(level="warning", title="保养临近",
                      detail="Model Y 距下次机油保养约 1,200 km"),
            AlertItem(level="info", title="胎压正常",
                      detail="四轮胎压均在标准区间"),
            AlertItem(level="info", title="驾驶行为良好",
                      detail="本周急加速/急刹车次数低于均值"),
        ],
    )
