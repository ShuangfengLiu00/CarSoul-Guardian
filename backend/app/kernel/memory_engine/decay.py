"""记忆衰减策略 — 不同类型记忆的保留和降权规则。

规则（C-06 因果纪律的衰减侧）：
  causal          : 永不衰减，永久保留（因果证据不可丢弃）
  correlational   : 30 天后降权（decay），90 天后删除（delete）
  state_snapshot  : 365 天后删除（delete），其余保留
  interaction     : 永不衰减，永久保留（审计要求）

返回值约定：
  "keep"   : 保留，不做处理
  "decay"  : 需要降权（降低 confidence / 排序权重）
  "delete" : 需要删除
"""
from __future__ import annotations

# 衰减规则：memory_type → (decay_after_days, delete_after_days)
# None 表示该阶段永不触发。
DECAY_RULES: dict[str, dict[str, int | None]] = {
    "causal": {"decay_after_days": None, "delete_after_days": None},
    "correlational": {"decay_after_days": 30, "delete_after_days": 90},
    "state_snapshot": {"decay_after_days": None, "delete_after_days": 365},
    "interaction": {"decay_after_days": None, "delete_after_days": None},
}


def get_decay_action(memory_type: str, age_days: int) -> str:
    """判断记忆是否需要衰减或删除。

    Parameters
    ----------
    memory_type : str
        记忆类型：causal / correlational / state_snapshot / interaction。
    age_days : int
        记忆距今的天数（>= 0）。

    Returns
    -------
    str
        "keep" / "decay" / "delete"。未知类型默认 "keep"（永不误删）。
    """
    rule = DECAY_RULES.get(memory_type)
    if rule is None:
        return "keep"  # 未知类型：保守保留，避免误删

    delete_after = rule["delete_after_days"]
    if delete_after is not None and age_days > delete_after:
        return "delete"

    decay_after = rule["decay_after_days"]
    if decay_after is not None and age_days > decay_after:
        return "decay"

    return "keep"
