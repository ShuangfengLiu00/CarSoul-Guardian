"""Guardian Agent 层 — 垂直 Agent 基类与合规闸门（TD-01 迁移）。

从 carModel 迁移的 Agent 调度逻辑，改造为 HTTP 调用 carModel 工具网关。
分层依赖（C-08）：agents -> kernel（向下），不反向。

模块：
  base.py        — BaseAgent / AgentContext / AgentResult（模板方法 run）
  compliance.py  — 5 类合规闸门（identity/geo/data_fraud/repair_mislead/safety_critical）
  llm_client.py  — Qwen2.5 / OpenAI 兼容 LLM 客户端
  vertical_base.py — 3 个 MVP 垂直 Agent 的共享底座
  battery_health_agent.py      — 电池健康（battery_health）
  driving_safety_agent.py      — 驾驶安全（driving_safety）
  charging_optimization_agent.py — 充电优化（charging_optimization）
"""
from app.agents.battery_health_agent import BatteryHealthAgent
from app.agents.charging_optimization_agent import ChargingOptimizationAgent
from app.agents.driving_safety_agent import DrivingSafetyAgent

__all__ = [
    "BatteryHealthAgent",
    "DrivingSafetyAgent",
    "ChargingOptimizationAgent",
]
