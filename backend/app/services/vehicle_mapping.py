"""Guardian 车辆 → carModel 车辆的「品牌精确映射」。

这是「整数 id 透传会张冠李戴」问题的根本修复：Guardian 用整数 id 管理车辆
（Tesla Model Y / BYD 汉EV），carModel 用 CSxxx 字符串 id（1002 辆仿真车），
两者原本无任何关联。早期用 ``f"CS{id:03d}"`` 偏移锚定，会把 Guardian 的
Tesla Model Y(id=1) 错配到 carModel 的 CS001(BYD Atto 3)，导致"自动检测到了
车，但品牌对不上"。

本模块按 **(brand, model)** 语义映射，是唯一 authoritative 来源。新增车辆时
在此表追加一行即可；映射缺失时回退偏移锚定（仍能返回一辆真车，只是品牌可能不符，
但绝不给假数据）。

映射目标均来自 carModel ``carsoul.db`` 的 ``vehicle_profile`` 表
（brand/model/year/capacity_kwh），用真实数据核对：
  · Tesla Model Y  → CS064 (Tesla Model Y 2024, 75kWh)  —— 对应 Guardian 本车 v1
  · BYD 汉 EV       → CS157 (BYD Han EV 2023,  85kWh)  —— 对应 Guardian v2

注意：键必须是 **Guardian 侧存储的原始字符串**（如 ``"汉 EV"`` 中文），
而非 carModel 侧的英文 ``"Han EV"``。
"""
from __future__ import annotations

from typing import Any

from app.core.config import settings

# (Guardian brand, Guardian model) -> carModel vehicle_id
GUARDIAN_BRAND_MODEL_TO_CARSOUL: dict[tuple[str, str], str] = {
    ("Tesla", "Model Y"): "CS064",
    ("BYD", "汉 EV"): "CS157",
}


def resolve_carsoul_id(
    vehicle: Any | None,
    *,
    default: str | None = None,
) -> str | None:
    """把 Guardian 车辆对象解析为 carModel CSxxx。

    解析优先级：
      1. ``(brand, model)`` 命中映射表 → 返回对应 CSxxx（品牌精确）；
      2. 映射缺失但有 id → 偏移锚定 ``f"CS{id:03d}"``（至少返回一辆真车）；
      3. 完全无本车（vehicle=None）→ 回退 ``default``（通常为
         ``CARSOUL_WORLD_DEFAULT_VEHICLE_ID``）；仍为空则返回 None，
         carModel 会如实反问「请告诉我车辆编号」，绝不拿随便一辆冒充本车。

    Args:
        vehicle: Guardian ``Vehicle`` ORM 对象（需含 brand/model/id），可空。
        default: 无本车时的兜底 CSxxx。

    Returns:
        carModel 车辆 id（如 ``"CS064"``），或 None。
    """
    if vehicle is None:
        return default or None

    key = (getattr(vehicle, "brand", None), getattr(vehicle, "model", None))
    if key in GUARDIAN_BRAND_MODEL_TO_CARSOUL:
        return GUARDIAN_BRAND_MODEL_TO_CARSOUL[key]

    # 映射缺失：偏移锚定，保证至少返回一辆真车（品牌可能不符，但绝不给假数据）。
    vid = getattr(vehicle, "id", None)
    if vid is not None:
        return f"CS{vid:03d}"
    return default or None
