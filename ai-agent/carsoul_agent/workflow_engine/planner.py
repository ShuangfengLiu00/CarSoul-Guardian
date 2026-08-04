"""Task Planner — 任务规划器 (§4.2).

Decomposes a high-level goal into a DAG (有向无环任务图) of executable
tasks. Each task is a node in the graph with dependencies; the engine
executes them respecting the dependency order, running independent
tasks in parallel.

Example task tree for "analyze_energy_consumption":

    Root: 车辆能耗异常分析
    ├── Task A: 电池健康检测      (parallel)
    ├── Task B: 驾驶行为分析      (parallel)
    ├── Task C: 环境影响分析      (parallel)
    └── Task D: 维修历史检查      (parallel)
         ↓ (all complete)
    Task E: 综合诊断              (depends on A,B,C,D)
         ↓
    Task F: 风险评估              (depends on E)
         ↓
    Task G: 建议生成              (depends on F)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from carsoul_agent.workflow_engine.intent import Intent


@dataclass
class Task:
    """A single task node in the DAG."""

    task_id: str
    name: str
    task_type: str             # perception / diagnosis / risk / explainer / service / judge
    agent_id: str              # which agent should handle this
    dependencies: list[str] = field(default_factory=list)  # task_ids this depends on
    parallel_group: str | None = None  # tasks in the same group run in parallel
    priority: int = 0          # higher = more important
    config: dict[str, Any] = field(default_factory=dict)  # extra task-specific config
    # Runtime fields (filled by the engine):
    state: str = "CREATED"     # CREATED → ASSIGNED → RUNNING → COMPLETED → VERIFIED
    result: dict[str, Any] | None = None
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "task_type": self.task_type,
            "agent_id": self.agent_id,
            "dependencies": self.dependencies,
            "parallel_group": self.parallel_group,
            "priority": self.priority,
            "state": self.state,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }


class TaskTree:
    """A DAG of tasks with dependency tracking.

    Supports topological execution: tasks with no unmet dependencies
    are ready to run; independent tasks can run in parallel.
    """

    def __init__(self, root_goal: str) -> None:
        self.root_goal = root_goal
        self._tasks: dict[str, Task] = {}
        self._order: list[str] = []  # insertion order for stable iteration

    def add_task(self, task: Task) -> None:
        self._tasks[task.task_id] = task
        self._order.append(task.task_id)

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def all_tasks(self) -> list[Task]:
        return [self._tasks[tid] for tid in self._order]

    def ready_tasks(self) -> list[Task]:
        """Tasks whose dependencies are all COMPLETED and that are still CREATED."""
        ready = []
        for task in self.all_tasks():
            if task.state != "CREATED":
                continue
            deps_met = all(
                self._tasks.get(dep) and self._tasks[dep].state == "COMPLETED"
                for dep in task.dependencies
            )
            if deps_met:
                ready.append(task)
        return ready

    def is_complete(self) -> bool:
        return all(t.state in ("COMPLETED", "VERIFIED") for t in self.all_tasks())

    def has_failed(self) -> bool:
        return any(t.state == "ERROR" and t.retry_count >= t.max_retries for t in self.all_tasks())

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_goal": self.root_goal,
            "task_count": len(self._tasks),
            "tasks": [t.to_dict() for t in self.all_tasks()],
        }


class TaskPlanner:
    """Decomposes an Intent into a TaskTree DAG (§4.2).

    Maps each scenario to a pre-defined task decomposition pattern,
    then returns a TaskTree ready for the execution engine.
    """

    def plan(self, intent: Intent) -> TaskTree:
        """Generate a task tree for the given intent."""
        scenario = intent.scenario
        planner_fn = _SCENARIO_PLANNERS.get(scenario, _plan_general)
        tree = planner_fn(intent)
        return tree


# ------------------------------------------------------------------ #
#  Scenario-specific planners
# ------------------------------------------------------------------ #
def _plan_long_trip(intent: Intent) -> TaskTree:
    """Long-trip pre-check: comprehensive multi-domain parallel analysis."""
    tree = TaskTree(f"长途出行前车辆健康检查 ({intent.trip_distance_km or 500}km)")

    # Phase 1: Parallel data collection & analysis
    tree.add_task(Task(
        task_id="t1_perception",
        name="状态感知·体征采集",
        task_type="perception",
        agent_id="perception",
        parallel_group="phase1",
        priority=10,
        config={"scenario": "long_trip", "distance_km": intent.trip_distance_km},
    ))
    tree.add_task(Task(
        task_id="t2_expert_panel",
        name="五专科专家并行会诊",
        task_type="diagnosis",
        agent_id="diagnosis",
        dependencies=["t1_perception"],
        parallel_group="phase2",
        priority=9,
        config={"scenario": "long_trip"},
    ))
    # Phase 2: Judge (conflict resolution if experts disagree)
    tree.add_task(Task(
        task_id="t3_judge",
        name="决策裁判·冲突仲裁",
        task_type="judge",
        agent_id="judge",
        dependencies=["t2_expert_panel"],
        priority=8,
        config={"trigger": "post_expert_panel"},
    ))
    # Phase 3: Risk assessment
    tree.add_task(Task(
        task_id="t4_risk",
        name="风险评估·量化等级",
        task_type="risk",
        agent_id="risk",
        dependencies=["t3_judge"],
        priority=7,
        config={"scenario": "long_trip", "distance_km": intent.trip_distance_km},
    ))
    # Phase 4: Explanation + report generation
    tree.add_task(Task(
        task_id="t5_explainer",
        name="解释生成·出行健康报告",
        task_type="explainer",
        agent_id="explainer",
        dependencies=["t4_risk"],
        priority=6,
        config={"report_type": "trip_report"},
    ))
    # Phase 5: Service actions
    tree.add_task(Task(
        task_id="t6_service",
        name="服务建议·处方与随访",
        task_type="service",
        agent_id="service",
        dependencies=["t5_explainer"],
        priority=5,
        config={"scenario": "long_trip"},
    ))
    return tree


def _plan_energy_anomaly(intent: Intent) -> TaskTree:
    """Energy anomaly: parallel battery + driving + maintenance analysis."""
    tree = TaskTree("车辆能耗异常分析")
    tree.add_task(Task(
        task_id="t1_perception", name="状态感知", task_type="perception",
        agent_id="perception", parallel_group="phase1", priority=10,
    ))
    tree.add_task(Task(
        task_id="t2_diagnosis", name="专家会诊·能耗根因", task_type="diagnosis",
        agent_id="diagnosis", dependencies=["t1_perception"], priority=9,
    ))
    tree.add_task(Task(
        task_id="t3_judge", name="决策裁判", task_type="judge",
        agent_id="judge", dependencies=["t2_diagnosis"], priority=8,
    ))
    tree.add_task(Task(
        task_id="t4_risk", name="风险评估", task_type="risk",
        agent_id="risk", dependencies=["t3_judge"], priority=7,
    ))
    tree.add_task(Task(
        task_id="t5_explainer", name="解释生成", task_type="explainer",
        agent_id="explainer", dependencies=["t4_risk"], priority=6,
    ))
    tree.add_task(Task(
        task_id="t6_service", name="服务建议", task_type="service",
        agent_id="service", dependencies=["t5_explainer"], priority=5,
    ))
    return tree


def _plan_battery_thermal(intent: Intent) -> TaskTree:
    """Battery thermal risk: urgent priority, safety-focused."""
    tree = TaskTree("电池热风险分析")
    tree.add_task(Task(
        task_id="t1_perception", name="状态感知·电池温控", task_type="perception",
        agent_id="perception", priority=10, config={"focus": "battery_thermal"},
    ))
    tree.add_task(Task(
        task_id="t2_diagnosis", name="专家会诊·热失控风险", task_type="diagnosis",
        agent_id="diagnosis", dependencies=["t1_perception"], priority=9,
    ))
    tree.add_task(Task(
        task_id="t3_judge", name="决策裁判", task_type="judge",
        agent_id="judge", dependencies=["t2_diagnosis"], priority=8,
    ))
    tree.add_task(Task(
        task_id="t4_risk", name="风险评估·热失控ETA", task_type="risk",
        agent_id="risk", dependencies=["t3_judge"], priority=7,
        config={"focus": "thermal_runaway"},
    ))
    tree.add_task(Task(
        task_id="t5_explainer", name="解释生成", task_type="explainer",
        agent_id="explainer", dependencies=["t4_risk"], priority=6,
    ))
    tree.add_task(Task(
        task_id="t6_service", name="服务建议·紧急干预", task_type="service",
        agent_id="service", dependencies=["t5_explainer"], priority=5,
        config={"urgency": "high"},
    ))
    return tree


def _plan_fault_diagnosis(intent: Intent) -> TaskTree:
    """General fault diagnosis."""
    tree = TaskTree("故障诊断")
    tree.add_task(Task(
        task_id="t1_perception", name="状态感知", task_type="perception",
        agent_id="perception", priority=10,
    ))
    tree.add_task(Task(
        task_id="t2_diagnosis", name="专家会诊", task_type="diagnosis",
        agent_id="diagnosis", dependencies=["t1_perception"], priority=9,
    ))
    tree.add_task(Task(
        task_id="t3_judge", name="决策裁判", task_type="judge",
        agent_id="judge", dependencies=["t2_diagnosis"], priority=8,
    ))
    tree.add_task(Task(
        task_id="t4_risk", name="风险评估", task_type="risk",
        agent_id="risk", dependencies=["t3_judge"], priority=7,
    ))
    tree.add_task(Task(
        task_id="t5_explainer", name="解释生成", task_type="explainer",
        agent_id="explainer", dependencies=["t4_risk"], priority=6,
    ))
    tree.add_task(Task(
        task_id="t6_service", name="服务建议", task_type="service",
        agent_id="service", dependencies=["t5_explainer"], priority=5,
    ))
    return tree


def _plan_maintenance(intent: Intent) -> TaskTree:
    """Maintenance planning."""
    tree = TaskTree("保养规划")
    tree.add_task(Task(
        task_id="t1_perception", name="状态感知", task_type="perception",
        agent_id="perception", priority=10,
    ))
    tree.add_task(Task(
        task_id="t2_diagnosis", name="专家会诊·保养评估", task_type="diagnosis",
        agent_id="diagnosis", dependencies=["t1_perception"], priority=9,
    ))
    tree.add_task(Task(
        task_id="t3_risk", name="风险评估", task_type="risk",
        agent_id="risk", dependencies=["t2_diagnosis"], priority=7,
    ))
    tree.add_task(Task(
        task_id="t4_explainer", name="解释生成·保养方案", task_type="explainer",
        agent_id="explainer", dependencies=["t3_risk"], priority=6,
    ))
    tree.add_task(Task(
        task_id="t5_service", name="服务建议·预约保养", task_type="service",
        agent_id="service", dependencies=["t4_explainer"], priority=5,
    ))
    return tree


def _plan_health_check(intent: Intent) -> TaskTree:
    """General health assessment."""
    tree = TaskTree("车辆健康评估")
    tree.add_task(Task(
        task_id="t1_perception", name="状态感知", task_type="perception",
        agent_id="perception", priority=10,
    ))
    tree.add_task(Task(
        task_id="t2_diagnosis", name="专家会诊", task_type="diagnosis",
        agent_id="diagnosis", dependencies=["t1_perception"], priority=9,
    ))
    tree.add_task(Task(
        task_id="t3_risk", name="风险评估", task_type="risk",
        agent_id="risk", dependencies=["t2_diagnosis"], priority=7,
    ))
    tree.add_task(Task(
        task_id="t4_explainer", name="解释生成·健康报告", task_type="explainer",
        agent_id="explainer", dependencies=["t3_risk"], priority=6,
    ))
    tree.add_task(Task(
        task_id="t5_service", name="服务建议", task_type="service",
        agent_id="service", dependencies=["t4_explainer"], priority=5,
    ))
    return tree


def _plan_general(intent: Intent) -> TaskTree:
    """Default: full five-step closed loop."""
    tree = TaskTree("车辆综合分析")
    tree.add_task(Task(
        task_id="t1_perception", name="状态感知", task_type="perception",
        agent_id="perception", priority=10,
    ))
    tree.add_task(Task(
        task_id="t2_diagnosis", name="专家会诊", task_type="diagnosis",
        agent_id="diagnosis", dependencies=["t1_perception"], priority=9,
    ))
    tree.add_task(Task(
        task_id="t3_judge", name="决策裁判", task_type="judge",
        agent_id="judge", dependencies=["t2_diagnosis"], priority=8,
    ))
    tree.add_task(Task(
        task_id="t4_risk", name="风险评估", task_type="risk",
        agent_id="risk", dependencies=["t3_judge"], priority=7,
    ))
    tree.add_task(Task(
        task_id="t5_explainer", name="解释生成", task_type="explainer",
        agent_id="explainer", dependencies=["t4_risk"], priority=6,
    ))
    tree.add_task(Task(
        task_id="t6_service", name="服务建议", task_type="service",
        agent_id="service", dependencies=["t5_explainer"], priority=5,
    ))
    return tree


# Scenario → planner mapping.
_SCENARIO_PLANNERS = {
    "long_trip": _plan_long_trip,
    "energy_anomaly": _plan_energy_anomaly,
    "battery_thermal": _plan_battery_thermal,
    "fault_diagnosis": _plan_fault_diagnosis,
    "maintenance": _plan_maintenance,
    "health_check": _plan_health_check,
    "chassis_check": _plan_fault_diagnosis,  # reuse fault diagnosis
    "general": _plan_general,
}
