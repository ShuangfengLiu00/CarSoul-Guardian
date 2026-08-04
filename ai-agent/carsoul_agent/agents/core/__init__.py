"""CarSoul Core Agent — AI 车辆医生 · 多智能体专家会诊.

This package implements the LangGraph-style state machine described in the
technical design, upgraded to an **AI Vehicle Doctor** with a multi-agent
expert panel:

    IN ─▶ perception ─▶ {anomaly?}
                         │ no  ─▶ explainer(normal) ─▶ END
                         │ yes ─▶ diagnosis(专家会诊) ─▶ risk ─▶ explainer ─▶ service ─▶ END

The diagnosis node now convenes a panel of five specialist agents
(动力/底盘/电气/驾驶行为/保养) that render parallel domain opinions,
then synthesises them into a unified consultation conclusion.

Shared ``AgentState`` flows between nodes; every step appends to
``trace_log`` so the full reasoning chain is replayable and auditable.

Five sub-agents (each a graph node function ``state -> state``):
    1. perception  — 状态感知 (问诊·体征采集: threshold + semantic detection)
    2. diagnosis   — 故障诊断 (专家会诊中枢: panel + synthesis)
    3. risk        — 风险评估 (量化等级 / probability / ETA)
    4. explainer   — 解释生成 (诊断报告: driver-profile-adapted language)
    5. service     — 服务建议 (处方·随访: guarded reminder / record / suggestion)

Expert panel (多智能体车辆专家系统):
    - PowertrainExpert      动力系统 (电池/发动机/电机)
    - ChassisExpert         底盘系统 (刹车/轮胎/悬挂)
    - ElectricalExpert      电气系统 (传感器/电路/电子)
    - DrivingBehaviorExpert 驾驶行为 (习惯/安全评分)
    - MaintenanceExpert     保养规划 (周期/成本/优先级)
"""
from carsoul_agent.agents.core.escalation import (
    EscalationConfig,
    EscalationManager,
    EscalationResult,
)
from carsoul_agent.agents.core.experts import (
    ChassisExpert,
    DrivingBehaviorExpert,
    ElectricalExpert,
    ExpertAgent,
    MaintenanceExpert,
    PowertrainExpert,
    build_expert_panel,
    run_expert_panel,
)
from carsoul_agent.agents.core.state import AgentState, Trace, trace_entry
from carsoul_agent.agents.core.workflow import CoreWorkflow, build_core_workflow

__all__ = [
    "AgentState",
    "Trace",
    "trace_entry",
    "CoreWorkflow",
    "build_core_workflow",
    "ExpertAgent",
    "PowertrainExpert",
    "ChassisExpert",
    "ElectricalExpert",
    "DrivingBehaviorExpert",
    "MaintenanceExpert",
    "build_expert_panel",
    "run_expert_panel",
    "EscalationConfig",
    "EscalationManager",
    "EscalationResult",
]
