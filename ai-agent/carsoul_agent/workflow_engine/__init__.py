"""CarSoul Agent Workflow Engine — 智能体工作流引擎 (V1.0).

Implements《CarSoul Agent Workflow Engine V1.0》: the task execution
hub that connects user needs → Orchestrator → Agent Team → Skills →
Tools → Digital Twin data.

    Goal → Plan → Execute → Verify → Act  (闭环)

Modules:
  - intent:        Intent Understanding (NL → goal/priority/scenario)
  - planner:       Task Planner (goal → DAG task tree)
  - router:        Agent Router (task → agent selection)
  - task_manager:  Task Manager (state machine, retry, fallback)
  - engine:        DAG Execution Engine (parallel/dynamic/failure recovery)
  - state_machine: Workflow-level state machine
  - memory:        Task Memory (per-task execution record)
"""
from carsoul_agent.workflow_engine.intent import Intent, IntentUnderstanding
from carsoul_agent.workflow_engine.planner import Task, TaskPlanner, TaskTree
from carsoul_agent.workflow_engine.router import AgentRouter
from carsoul_agent.workflow_engine.task_manager import TaskManager, TaskState
from carsoul_agent.workflow_engine.engine import WorkflowEngine
from carsoul_agent.workflow_engine.state_machine import WorkflowState, WorkflowStateMachine
from carsoul_agent.workflow_engine.memory import TaskMemory

__all__ = [
    "Intent",
    "IntentUnderstanding",
    "Task",
    "TaskPlanner",
    "TaskTree",
    "AgentRouter",
    "TaskManager",
    "TaskState",
    "WorkflowEngine",
    "WorkflowState",
    "WorkflowStateMachine",
    "TaskMemory",
]
