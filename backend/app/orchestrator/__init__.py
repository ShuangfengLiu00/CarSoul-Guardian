"""Orchestrator 总控调度器包。

导出 Orchestrator 及其输入输出契约类型。
不执行业务逻辑，只做意图识别 -> 任务分解 -> Agent 路由 -> 结果聚合 -> 合规终审。
"""
from app.orchestrator.dispatcher import (  # noqa: F401
    IntentResult,
    Orchestrator,
    OrchestratorResult,
    SubTask,
)

__all__ = ["Orchestrator", "OrchestratorResult", "IntentResult", "SubTask"]
