"""Health API: dashboard overview data.

诚实数据原则：**能从 carModel 真实端点取的就取真的；取不到的不许留假值。**

这个接口是整个产品的门面（Dashboard 首页）。历史版本里 ``health_score=92``
和三条 ``recent_alerts``（"保养临近约 1,200km" / "胎压正常" / "驾驶行为良好"）
全部是硬编码编出来的 —— carModel 的数据模型里**根本没有胎压这一项**，
那句"四轮胎压均在标准区间"是彻头彻尾的虚构。用户在首页看到的每一个判断
都建立在假地基上。

现在的口径：
  - 真值一律来自 carModel ``GET /world/state/{vehicle_id}``；
  - 取不到就返回 ``health_score=None`` + ``recent_alerts=[]`` + 明确的
    ``data_status``，由 UI 显示"暂无数据"；
  - 每条告警都带 ``source`` 与触发它的真实数值/判定依据，可溯源。

宁可空着，也不能编。
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.config import settings
from app.schemas.health import AlertItem, DataStatus, HealthOverview
from app.services import agent_service, carsoul_world

router = APIRouter()

_STATE_SOURCE = "carmodel:/world/state"

# Guardian 侧的呈现阈值。必须随告警文案一起暴露给用户 —— 不允许"神秘阈值"。
_TEMP_WARNING = 40.0
_TEMP_CRITICAL = 45.0
_RISK_WARNING = 0.30
_RISK_CRITICAL = 0.60

# carModel ``state_summary.top_concerns`` 的取值域与触发条件，逐条核对自
# carModel/encoder/state_encoder.py:189-201。未收录的代码**原样透出**，
# 绝不替世界模型编一个好听的解释。
_CONCERN_LABELS: dict[str, tuple[str, str]] = {
    "extreme_temp": ("环境温度极端", "近期环境温度均值低于 5℃ 或高于 35℃"),
    "high_fast_charge": ("快充占比偏高", "近期快充比例均值超过 50%"),
    "aggressive_drive": ("驾驶风格激进", "车辆档案标记 driving_style=aggressive"),
    "low_soh": ("电池健康度偏低", "SOH 低于 80%"),
    "recent_failure": ("近期发生过故障", "近 30 天存在故障记录"),
    "fast_degradation": ("退化速率偏快", "日均 SOH 退化率超过 0.0008"),
}

# carModel 没有对 concerns 分级，下面的等级是 **Guardian 的呈现策略**，
# 不是世界模型的判定结论，因此 detail 里会注明代码出处。
_CONCERN_LEVEL: dict[str, str] = {
    "low_soh": "warning",
    "fast_degradation": "warning",
    "recent_failure": "warning",
}


def _build_alerts(state: dict) -> list[AlertItem]:
    """只从 carModel 的真实字段派生告警，每条都带真实数值与判定依据。"""
    summary = state.get("state_summary") or {}
    battery = state.get("battery") or {}
    alerts: list[AlertItem] = []

    # 1) 生命阶段 —— carModel 自己的分级（encoder/state_encoder.py:_life_stage）
    life_stage = summary.get("life_stage")
    if life_stage == "eol":
        alerts.append(AlertItem(
            level="critical",
            title="电池已进入寿命终止阶段",
            detail="carModel 判定 life_stage=eol（SOH 低于 75%）。",
            source=f"{_STATE_SOURCE}#state_summary.life_stage",
        ))
    elif life_stage == "late":
        alerts.append(AlertItem(
            level="warning",
            title="电池进入生命后期",
            detail="carModel 判定 life_stage=late（SOH 介于 75%~85%）。",
            source=f"{_STATE_SOURCE}#state_summary.life_stage",
        ))

    # 2) 世界模型给出的关注项
    for code in summary.get("top_concerns") or []:
        label, basis = _CONCERN_LABELS.get(
            code, (str(code), "carModel 未收录的关注项代码，原样透出")
        )
        alerts.append(AlertItem(
            level=_CONCERN_LEVEL.get(code, "info"),
            title=label,
            detail=f"{basis}（carModel 关注项代码 {code}）。",
            source=f"{_STATE_SOURCE}#state_summary.top_concerns",
        ))

    # 3) 风险分 —— carModel 自己的 0-1 风险度量
    risk = summary.get("risk_score")
    if isinstance(risk, (int, float)):
        if risk >= _RISK_CRITICAL:
            level = "critical"
        elif risk >= _RISK_WARNING:
            level = "warning"
        else:
            level = "info"
        alerts.append(AlertItem(
            level=level,
            title=f"综合风险分 {risk:.2f}",
            detail=(
                f"carModel 风险分 {risk:.2f}（0-1，越高越危险；Guardian 呈现阈值："
                f"≥{_RISK_WARNING} 警告、≥{_RISK_CRITICAL} 严重）。"
                "该分数来自仿真训练模型，未经真实数据校准，不构成决策依据。"
            ),
            source=f"{_STATE_SOURCE}#state_summary.risk_score",
        ))

    # 4) 电池温度 —— 直接观测值
    temp = battery.get("temperature")
    if isinstance(temp, (int, float)):
        if temp >= _TEMP_CRITICAL:
            alerts.append(AlertItem(
                level="critical",
                title="电池温度过高",
                detail=f"当前电池温度 {temp}℃，超过严重阈值 {_TEMP_CRITICAL}℃。",
                source=f"{_STATE_SOURCE}#battery.temperature",
            ))
        elif temp >= _TEMP_WARNING:
            alerts.append(AlertItem(
                level="warning",
                title="电池温度偏高",
                detail=f"当前电池温度 {temp}℃，超过警告阈值 {_TEMP_WARNING}℃。",
                source=f"{_STATE_SOURCE}#battery.temperature",
            ))

    # 什么都没触发时，如实说明"检查了什么、数据截至何时"，
    # 而不是像历史版本那样编一条"胎压正常"来撑场面。
    if not alerts:
        soh = battery.get("soh")
        checked = f"SOH={soh}%" if isinstance(soh, (int, float)) else "SOH 缺失"
        alerts.append(AlertItem(
            level="info",
            title="未触发任何告警阈值",
            detail=(
                f"已检查电池健康度（{checked}）、电池温度、生命阶段与世界模型关注项，"
                f"数据截至 {state.get('as_of') or '未知'}。"
            ),
            source=_STATE_SOURCE,
        ))

    return alerts


@router.get("/overview", response_model=HealthOverview)
async def overview(
    vehicle_id: str | None = Query(
        None,
        description="carModel 侧的 vehicle_id（如 CS001）。不传则无法获取真实车况，"
                    "health_score 返回 null，UI 应显示「暂无数据」。",
    ),
) -> HealthOverview:
    # agent_status 曾硬编码 "active" —— 那是 Dashboard 死绿灯的真正源头。
    # 现如实上报**最近一次真实观测到**的大模型链路状态；在任何一轮对话真正
    # 发生之前为 "unknown"（未观测即不表态）。
    agent_status = agent_service.get_last_link_state()["agent_status"]

    # 调用方没指定就用配置里的缺省车（默认留空 = 不猜）。
    resolved_id = (vehicle_id or settings.CARSOUL_WORLD_DEFAULT_VEHICLE_ID or "").strip()
    used_default = bool(not vehicle_id and resolved_id)

    if not resolved_id:
        return HealthOverview(
            agent_status=agent_status,
            data_status=DataStatus(
                code="no_vehicle_selected",
                detail="未指定 vehicle_id 且未配置 CARSOUL_WORLD_DEFAULT_VEHICLE_ID，"
                       "无法从 carModel 获取真实车况；健康分与告警均无数据"
                       "（此处不提供任何默认值）。",
            ),
        )
    vehicle_id = resolved_id

    state = await carsoul_world.vehicle_state(vehicle_id)
    if not isinstance(state, dict) or "error" in state:
        err = (state or {}).get("error", "world_model_unavailable")
        detail = str((state or {}).get("detail", ""))[:200]
        return HealthOverview(
            agent_status=agent_status,
            vehicle_id=vehicle_id,
            data_status=DataStatus(
                code="carmodel_unavailable",
                detail=f"carModel 取车况失败（{err}）：{detail}；健康分与告警均无数据。",
            ),
        )

    summary = state.get("state_summary") or {}
    raw_score = summary.get("health_score")
    alerts = _build_alerts(state)

    if not isinstance(raw_score, (int, float)):
        return HealthOverview(
            agent_status=agent_status,
            vehicle_id=vehicle_id,
            as_of=state.get("as_of"),
            recent_alerts=alerts,
            data_source=_STATE_SOURCE,
            data_status=DataStatus(
                code="carmodel_state_incomplete",
                detail="carModel 返回了车况但缺少 state_summary.health_score"
                       "（通常是该车尚未生成 embedding）；健康分无数据。",
            ),
        )

    # carModel 的 health_score 口径是 0-1（encoder/state_encoder.py:153）。
    # 与 carModel 自己的量纲防御保持一致（agent/agent.py:186）：万一上游改成
    # 百分比量纲，按百分比处理，绝不静默乘出一个 8080 分。
    score = float(raw_score)
    health_score = round(score) if score > 1.0 else round(score * 100)

    return HealthOverview(
        health_score=health_score,
        health_score_basis=(
            "carModel state_summary.health_score × 100"
            "（口径 = clamp((SOH−0.60)/0.40, 0, 1)，见 carModel encoder/state_encoder.py:153）"
        ),
        agent_status=agent_status,
        recent_alerts=alerts,
        vehicle_id=vehicle_id,
        as_of=state.get("as_of"),
        data_source=_STATE_SOURCE,
        data_status=DataStatus(
            code="ok_carmodel_state",
            detail=(
                f"健康分与告警均来自 carModel {_STATE_SOURCE} 的真实车况"
                f"（车辆 {vehicle_id}"
                + ("，来自 CARSOUL_WORLD_DEFAULT_VEHICLE_ID 配置的缺省车" if used_default else "")
                + "）。"
            ),
        ),
    )
