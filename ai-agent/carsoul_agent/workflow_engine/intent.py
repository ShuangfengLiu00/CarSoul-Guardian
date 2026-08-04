"""Intent Understanding Module — 用户意图理解 (§4.1).

Converts a natural-language user message into a structured intent:

    > "我的车最近越来越耗电，是什么原因？"

becomes:

    {
      "goal": "analyze_energy_consumption",
      "vehicle": "car001",
      "priority": "medium",
      "scenario": "energy_anomaly"
    }

The intent drives the Task Planner's task-tree decomposition.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Intent:
    """Structured user intent parsed from natural language."""

    goal: str                       # canonical goal identifier
    goal_label: str                 # human-readable goal
    vehicle_id: str = "car001"
    priority: str = "medium"        # low / medium / high / urgent
    scenario: str = "general"       # general / energy_anomaly / battery_thermal /
                                    # long_trip / maintenance / knowledge_query
    raw_message: str = ""
    detected_keywords: list[str] = field(default_factory=list)
    trip_distance_km: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "goal_label": self.goal_label,
            "vehicle_id": self.vehicle_id,
            "priority": self.priority,
            "scenario": self.scenario,
            "raw_message": self.raw_message,
            "detected_keywords": self.detected_keywords,
            "trip_distance_km": self.trip_distance_km,
        }


# ---- Scenario detection rules ----------------------------------------- #
# Each rule: (keyword_list, scenario, goal, goal_label, priority)
_SCENARIO_RULES: list[dict[str, Any]] = [
    {
        "keywords": ["长途", "自驾", "出行", "出差", "旅游", "高速", "公里", "千米", "km",
                      "trip", "travel", "自驾游", "回老家", "跑长途", "远行", "公路旅行",
                      "下周", "明天出发", "准备出门", "上路"],
        "scenario": "long_trip",
        "goal": "pre_trip_health_check",
        "goal_label": "长途出行前车辆健康检查",
        "priority": "high",
    },
    {
        "keywords": ["耗电", "掉电", "续航下降", "续航", "energy", "电耗"],
        "scenario": "energy_anomaly",
        "goal": "analyze_energy_consumption",
        "goal_label": "能耗异常分析",
        "priority": "medium",
    },
    {
        "keywords": ["电池", "battery", "温度", "temperature", "发热", "热失控", "battery_temp"],
        "scenario": "battery_thermal",
        "goal": "battery_thermal_analysis",
        "goal_label": "电池热风险分析",
        "priority": "high",
    },
    {
        "keywords": ["故障", "报警", "灯亮", "fault", "warning", "异常", "error"],
        "scenario": "fault_diagnosis",
        "goal": "fault_diagnosis",
        "goal_label": "故障诊断",
        "priority": "high",
    },
    {
        "keywords": ["保养", "maintenance", "换油", "机油", "保养计划", "维护"],
        "scenario": "maintenance",
        "goal": "maintenance_planning",
        "goal_label": "保养规划",
        "priority": "medium",
    },
    {
        "keywords": ["健康", "状态", "怎么样", "体检", "health", "score"],
        "scenario": "health_check",
        "goal": "vehicle_health_assessment",
        "goal_label": "车辆健康评估",
        "priority": "medium",
    },
    {
        "keywords": ["多久换", "什么时候换", "怎么", "如何", "为什么", "区别", "是什么",
                      "正常吗", "对吗", "可以吗", "需要吗", "多少公里", "周期", "寿命",
                      "建议", "推荐", "注意", "科普", "知识", "讲解", "解释"],
        "scenario": "knowledge_query",
        "goal": "knowledge_retrieval",
        "goal_label": "汽车知识问答",
        "priority": "low",
    },
    {
        "keywords": ["刹车", "轮胎", "胎压", "brake", "tire"],
        "scenario": "chassis_check",
        "goal": "chassis_inspection",
        "goal_label": "底盘系统检查",
        "priority": "medium",
    },
]


class IntentUnderstanding:
    """Parses natural language into a structured Intent (§4.1)."""

    def parse(self, message: str, vehicle_id: str = "car001") -> Intent:
        """Convert a user message into a structured intent."""
        msg = (message or "").strip().lower()
        detected: list[str] = []

        # Match against scenario rules (first match wins, but we collect
        # all matched keywords for transparency).
        best_scenario = "general"
        best_goal = "vehicle_analysis"
        best_label = "车辆综合分析"
        best_priority = "medium"

        for rule in _SCENARIO_RULES:
            matched = [k for k in rule["keywords"] if k in msg]
            if matched:
                detected.extend(matched)
                # Long-trip takes priority over energy/battery scenarios
                # because it's a superset (includes pre-trip battery check).
                if rule["scenario"] == "long_trip":
                    best_scenario = rule["scenario"]
                    best_goal = rule["goal"]
                    best_label = rule["goal_label"]
                    best_priority = rule["priority"]
                    break
                # First non-long-trip match.
                if best_scenario == "general":
                    best_scenario = rule["scenario"]
                    best_goal = rule["goal"]
                    best_label = rule["goal_label"]
                    best_priority = rule["priority"]

        # Extract trip distance if present.
        trip_distance = None
        if best_scenario == "long_trip":
            for pat in [r"(\d+)\s*公里", r"(\d+)\s*千米", r"(\d+)\s*km"]:
                m = re.search(pat, msg)
                if m:
                    trip_distance = int(m.group(1))
                    break

        # Adjust priority for urgent keywords.
        if any(k in msg for k in ["紧急", "危险", "冒烟", "urgent", "danger"]):
            best_priority = "urgent"

        return Intent(
            goal=best_goal,
            goal_label=best_label,
            vehicle_id=vehicle_id,
            priority=best_priority,
            scenario=best_scenario,
            raw_message=message,
            detected_keywords=list(set(detected)),
            trip_distance_km=trip_distance,
        )
