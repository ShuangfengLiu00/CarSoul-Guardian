"""Health overview schemas (Dashboard data)."""
from __future__ import annotations

from pydantic import BaseModel


class AlertItem(BaseModel):
    level: str  # info | warning | critical
    title: str
    detail: str = ""


class HealthOverview(BaseModel):
    health_score: int  # 0-100
    agent_status: str  # active | idle | standby
    recent_alerts: list[AlertItem] = []
