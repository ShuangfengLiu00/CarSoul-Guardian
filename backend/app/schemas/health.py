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


class AgentLinkState(BaseModel):
    """最近一次**真实观测到**的大模型链路状态。

    存在的意义：``agent_status`` 只有 active/degraded/unknown 三档，无法区分
    "链路挂了导致回答变差" 和 "链路挂了但这轮是合规拒答、回答本就不该经大模型"。
    只给三档会逼 UI 把后者也说成"降级运行"，那是把一次正常的合规拒答污名化。
    这里把两个正交事实分开摆出来，让 UI 能说人话。
    """

    llm_available: bool = Field(description="最近一轮观测到的链路是否可用")
    llm_used: bool = Field(description="最近一轮是否真的调用了大模型")
    affects_last_turn: bool = Field(
        description="最近一轮的回答是否**真的**因链路不可用而受损"
                    "（= degraded.affects_this_turn）。确定性路径为 false。",
    )
    engine: str = Field(
        "unknown", description="carmodel_agent_chat / local_agent / offline_fallback / unknown"
    )
    reason: str | None = Field(None, description="降级原因码，未降级为 None")
    observed_at: str | None = Field(
        None, description="观测时间（UTC ISO8601）。为 None 表示尚未发生过任何一轮对话。"
    )


class HealthOverview(BaseModel):
    # None = 取不到真实车况。**不允许**用常量兜底（历史版本硬编码 92）。
    # 收敛 P1：health_score 是「车辆健康分(VHS)」的保留字段。overview 是 carModel
    # 世界模型作用域的端点，无法计算 Guardian VHS，故恒为 None；前端车辆健康分
    # 应改取 /api/vehicle/{id}/health-score。这样「health_score」字段名在全站
    # 始终只有 VHS 一个定义，杜绝与 carModel 世界模型 SOH 健康互相冒充。
    health_score: int | None = Field(
        None, description="车辆综合健康分(VHS)。由 /api/vehicle/{id}/health-score 统一提供；"
                          "overview 为世界模型作用域端点，不在此重复定义，恒为 None。"
    )
    # 收敛 P1：carModel 世界模型对该仿真车的 SOH 健康评估，是**另一套定义**，
    # 绝不等同于车辆物理健康分。仅用于「世界模型引擎健康分」展示。
    world_model_soh_health: float | None = Field(
        None,
        description="carModel 世界模型对该仿真车的 SOH 健康评估(0-100)。"
        "口径 = clamp((SOH−0.60)/0.40, 0, 1)×100（carModel encoder/state_encoder.py:153）。"
        "与 VHS 是不同定义，仅供『世界模型引擎健康分』展示，不可等同于车辆真实车况。",
    )
    health_score_basis: str | None = Field(
        None, description="world_model_soh_health 的来源与口径，便于用户判断这个数字可不可信。"
    )
    agent_status: str  # active | degraded | unknown
    agent_link: AgentLinkState | None = Field(
        None,
        description="链路状态明细。为 None 表示尚未观测过（等价于 agent_status=unknown）。",
    )
    recent_alerts: list[AlertItem] = []
    vehicle_id: str | None = None
    as_of: str | None = Field(
        None, description="车况数据在 carModel 侧的观测时间。"
    )
    data_source: str | None = Field(
        None, description="真实数据来源端点；为 None 表示本次没有取到任何真实车况。"
    )
    data_status: DataStatus
