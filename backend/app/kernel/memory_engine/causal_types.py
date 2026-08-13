"""因果事件类型字典 — 定义标准因果事件模板。

每个事件类型包含 5 个字段：
  - impact_target: 影响目标（被影响的车辆维度，如 battery_soh）
  - impact_delta: 影响量级（正=退化，负=改善）
  - confidence: 置信度（0.0-1.0）
  - causality_grade: causal / correlational / insufficient_data
  - mechanism: 因果机理描述（causal 必填，correlational 必须为 None）

C-06 因果纪律：causal 事件必须提供 mechanism；correlational 事件
禁止提供 mechanism（禁止因果句式）。本字典中的模板在导入时即校验。
"""
from __future__ import annotations

from typing import Any

# 每个模板必须包含的 5 个字段。
_REQUIRED_FIELDS = (
    "impact_target",
    "impact_delta",
    "confidence",
    "causality_grade",
    "mechanism",
)

CAUSAL_EVENT_TYPES: dict[str, dict[str, Any]] = {
    # ── 电池衰减因果链 ──
    "fast_charge_session": {
        "impact_target": "battery_soh",
        "impact_delta": -0.02,
        "confidence": 0.85,
        "causality_grade": "causal",
        "mechanism": "快充导致锂枝晶生长，加速固态电解质界面膜(SEI)增厚，活性锂损失",
    },
    "deep_discharge_event": {
        "impact_target": "battery_soh",
        "impact_delta": -0.05,
        "confidence": 0.80,
        "causality_grade": "causal",
        "mechanism": "深放电导致低电压下活性物质溶解",
    },
    "high_temp_operation": {
        "impact_target": "battery_soh",
        "impact_delta": -0.01,
        "confidence": 0.75,
        "causality_grade": "causal",
        "mechanism": "高温加速电解液分解和化学老化",
    },
    "slow_charge_session": {
        "impact_target": "battery_soh",
        "impact_delta": 0.001,
        "confidence": 0.60,
        "causality_grade": "causal",
        "mechanism": "慢充减少热应力，对电池健康有轻微正向影响",
    },
    # ── 驾驶行为因果链 ──
    "hard_acceleration": {
        "impact_target": "motor_wear",
        "impact_delta": 0.01,
        "confidence": 0.60,
        "causality_grade": "correlational",  # 相关性，非因果
        "mechanism": None,  # 禁止因果句式
    },
    "harsh_braking": {
        "impact_target": "brake_pad_wear",
        "impact_delta": 0.02,
        "confidence": 0.70,
        "causality_grade": "causal",
        "mechanism": "急刹车导致刹车片摩擦材料物理磨损",
    },
    # ── 维保干预因果链 ──
    "maintenance_intervention": {
        "impact_target": "battery_soh",
        "impact_delta": 0.5,
        "confidence": 0.90,
        "causality_grade": "causal",
        "mechanism": "维保干预（换件/校准）恢复电池健康度",
    },
    "software_update": {
        "impact_target": "battery_soh",
        "impact_delta": 0.1,
        "confidence": 0.75,
        "causality_grade": "causal",
        "mechanism": "BMS 软件升级优化充放电策略",
    },
}


def _validate() -> None:
    """导入时校验所有模板字段完整且符合 C-06 因果纪律。"""
    for etype, tmpl in CAUSAL_EVENT_TYPES.items():
        missing = [f for f in _REQUIRED_FIELDS if f not in tmpl]
        assert not missing, f"causal_types: {etype} 缺少字段 {missing}"
        grade = tmpl["causality_grade"]
        mech = tmpl["mechanism"]
        if grade == "causal":
            assert mech, f"causal_types: {etype} 为 causal 但 mechanism 为空"
        elif grade == "correlational":
            assert mech is None, (
                f"causal_types: {etype} 为 correlational 但 mechanism 非空"
            )


_validate()


def get_event_template(event_type: str) -> dict[str, Any] | None:
    """获取事件模板。未定义返回 None。"""
    return CAUSAL_EVENT_TYPES.get(event_type)
