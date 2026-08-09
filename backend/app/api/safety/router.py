"""Safety API: 合规闸门真实拦截计数。

为什么是转发而不是 Guardian 自己数
----------------------------------
合规闸门跑在 **carModel 进程内**（``agent/agent.py::_compliance_hit``，L564-592），
Guardian 与 carModel 是两个独立进程、靠 HTTP 通信（见
``app/services/carsoul_world.py``）。真实拦截事件只在 carModel 侧可见，
所以计数必须记在那边，Guardian 只做搬运。

如果在 Guardian 里另起一个计数器，它数到的只是"经 Guardian 转发且 Guardian
识别出 compliance_category 的那部分"——carModel 被其他调用方直接访问的拦截
一律漏掉，前端看到的"累计拦截"会系统性偏小。一个说不清口径的数字，
比没有数字更糟。

拿不到就说拿不到
----------------
上游 503 / 不可达时返回 ``source="unavailable"`` + 全部计数为 ``null``，
**不回填 0**。这条页面（``/safety``）整改前正是 433 行硬编码假自证，
在这里补一个"看起来很干净的 0"等于换个姿势重演同一个问题。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from app.schemas.safety import GateStats, GateStatsDataStatus
from app.services import carsoul_world

router = APIRouter()

logger = logging.getLogger(__name__)

_SOURCE = "carmodel:/agent/compliance/gate-stats"

# 5 类闸门类别，逐条对应 carModel agent/agent.py::COMPLIANCE_ACTIONS (L546-552)
_CATEGORIES = ("identity", "geo", "data_fraud", "repair_mislead", "safety_critical")


def _unavailable(code: str, detail: str) -> GateStats:
    """取不到真值时的响应：计数全部 None，source 明确标 unavailable。"""
    return GateStats(
        source="unavailable",
        data_source=_SOURCE,
        data_status=GateStatsDataStatus(code=code, detail=detail),
    )


@router.get("/gate-stats", response_model=GateStats)
async def gate_stats() -> GateStats:
    """返回 5 类合规闸门的**真实累计拦截次数**。

    每一个数字都对应一次真实发生过的拦截：carModel 在 ``_compliance_hit``
    命中后由 ``_record_gate_hit`` 落盘计数（只记类别与次数）。

    隐私（PIPL）：本端点**不提供也无法提供**被拦截问句的明细——carModel 侧
    的计数表里根本没有承载用户输入的列。明细审计（S8）属法务范围。
    """
    raw = await carsoul_world.compliance_gate_stats()

    if not isinstance(raw, dict) or "error" in raw:
        err = (raw or {}).get("error", "world_model_unavailable")
        detail = str((raw or {}).get("detail", ""))[:200]
        logger.warning("carModel gate-stats 不可达 (%s): %s", err, detail)
        return _unavailable(
            "carmodel_unavailable",
            f"carModel 合规计数取数失败（{err}）：{detail}；"
            "按诚实数据纪律不回填 0，请显示「暂无数据」。",
        )

    # 上游契约校验：字段缺失/类型不对就当拿不到，绝不用 0 兜底把问题藏起来
    missing = [c for c in _CATEGORIES if not isinstance(raw.get(c), int)]
    if missing or not isinstance(raw.get("total"), int):
        logger.error("carModel gate-stats 响应不符合契约，缺失或非整型字段: %s", missing)
        return _unavailable(
            "carmodel_payload_invalid",
            f"carModel 返回体缺少合法计数字段 {missing or ['total']}（疑似上游版本不匹配）；"
            "不猜测数值，请显示「暂无数据」。",
        )

    counts = {c: int(raw[c]) for c in _CATEGORIES}
    storage = raw.get("storage")
    degraded_reason = raw.get("degraded_reason")

    # carModel 退到进程内计数时该值偏小且重启清零 —— 必须透到 UI，不能默默展示
    if storage == "memory" and not degraded_reason:
        degraded_reason = "carModel 计数未落盘（进程内），该值重启即清零且可能偏小"

    ok_detail = (
        f"计数来自 carModel {_SOURCE} 的真实拦截事件"
        f"（记录点 agent/agent.py::_record_gate_hit）。"
        f"统计窗口自 {raw.get('since') or '尚无拦截记录'} 起。"
        "仅含类别计数，不含任何用户输入明细。"
    )
    if degraded_reason:
        ok_detail += f" 注意：{degraded_reason}"

    return GateStats(
        total=int(raw["total"]),
        **counts,
        source="real",
        since=raw.get("since"),
        updated_at=raw.get("updated_at"),
        storage=storage,
        degraded_reason=degraded_reason,
        data_source=_SOURCE,
        data_status=GateStatsDataStatus(code="ok_carmodel_gate_stats", detail=ok_detail),
    )
