"""Orchestrator 路由表 — 意图关键词到目标 Agent 的映射。

5 个垂直 Agent：3 个 MVP 启用，2 个阶段 2 禁用。
规则路由优先（WARN-02）：关键词未命中才走 LLM 兜底。
"""
from __future__ import annotations

ROUTING_TABLE: dict[str, dict] = {
    "battery_health": {
        "agent_name": "battery_health",
        "keywords": [
            "电池", "健康", "SOH", "soh", "衰减", "寿命", "续航", "电池健康",
            "健康度", "容量", "电池包", "归因", "剩余寿命", "老化", "电量",
        ],
        "enabled": True,
        "description": "电池健康度（SOH）与寿命分析",
    },
    "driving_safety": {
        "agent_name": "driving_safety",
        "keywords": [
            "驾驶", "安全", "急加速", "急刹车", "疲劳", "行为", "评分", "习惯",
            "DMS", "dms", "驾驶评分", "驾驶行为", "制动", "风险驾驶",
        ],
        "enabled": True,
        "description": "驾驶行为分析与安全评分",
    },
    "charging_optimization": {
        "agent_name": "charging_optimization",
        "keywords": [
            "充电", "快充", "慢充", "充电桩", "充电策略", "充电优化", "充电习惯",
            "充电建议", "补能", "充电规划",
        ],
        "enabled": True,
        "description": "充电策略优化",
    },
    "insurance_risk": {
        "agent_name": "insurance_risk",
        "keywords": ["保险", "理赔", "出险", "保费", "事故风险", "保险风险"],
        "enabled": False,
        "description": "保险风险评估（阶段 2）",
    },
    "used_car_valuation": {
        "agent_name": "used_car_valuation",
        "keywords": [
            "残值", "估值", "二手车", "评估", "贬值", "保值", "二手车价值",
            "卖多少钱", "值多少",
        ],
        "enabled": False,
        "description": "二手车残值评估（阶段 2）",
    },
}

# 阶段 2 Agent 的兜底回复。
DISABLED_AGENT_REPLY = "该功能将在阶段 2 上线，当前版本暂不支持。"

# 已启用 Agent 名称列表（供 LLM 兜底选项与校验使用）。
ENABLED_AGENTS = [k for k, v in ROUTING_TABLE.items() if v["enabled"]]
