"""Health overview schemas (Dashboard data).

诚实数据原则：**拿不到真值的字段一律为 None**，让 UI 显示"暂无数据"，
绝不用好看的常量填充。每个数值都必须能说清它从哪来、按什么口径算的。
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class AlertItem(BaseModel):
    level: str  # info | warning | critical
    title: str
    detail: str = ""
    source: str | None = Field(
        None,
        description="该条告警的数据来源（如 carmodel:/world/state），便于溯源。"
                    "为 None 表示来源未标注——不应出现在新代码里。",
    )


class DataStatus(BaseModel):
    """本次 overview 的数据真实性说明。

    UI 必须据此决定"显示真值"还是"显示暂无数据"，不允许自行脑补兜底值。
    """

    code: str = Field(
        description="ok_carmodel_state | no_vehicle_selected | "
                    "carmodel_unavailable | carmodel_state_incomplete",
    )
    detail: str = ""


class HealthOverview(BaseModel):
    # None = 取不到真实车况。**不允许**用常量兜底（历史版本硬编码 92）。
    health_score: int | None = Field(
        None, description="0-100 综合健康分。取不到真实车况时为 None。"
    )
    health_score_basis: str | None = Field(
        None, description="健康分的来源与口径，便于用户判断这个数字可不可信。"
    )
    agent_status: str  # active | degraded | unknown
    recent_alerts: list[AlertItem] = []
    vehicle_id: str | None = None
    as_of: str | None = Field(
        None, description="车况数据在 carModel 侧的观测时间。"
    )
    data_source: str | None = Field(
        None, description="真实数据来源端点；为 None 表示本次没有取到任何真实车况。"
    )
    data_status: DataStatus
