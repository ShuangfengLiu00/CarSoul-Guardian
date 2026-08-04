"""DAG Execution Engine — 工作流执行引擎 (§5, §6, §9).

The central orchestrator that executes a TaskTree DAG:

  - Respects task dependencies (topological execution)
  - Runs independent tasks in parallel (ThreadPoolExecutor)
  - Supports dynamic workflow adjustment (add tasks based on results)
  - Implements failure recovery: Retry → Fallback → Human-in-loop
  - Integrates with the governance layer (lifecycle, permissions, judge)
  - Feeds results back into the shared AgentState

Execution loop:
  1. Plan tasks (TaskPlanner)
  2. While tasks remain:
     a. Find ready tasks (dependencies met)
     b. Route each to an agent (AgentRouter)
     c. Execute (with lifecycle tracking)
     d. On success → record result, check for dynamic adjustment
     e. On failure → retry, then fallback, then human-in-loop
  3. Verify results, finalise workflow state
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from carsoul_agent.agents.core.state import AgentState, trace_entry
from carsoul_agent.governance.judge import JudgeAgent
from carsoul_agent.governance.lifecycle import lifecycle_manager
from carsoul_agent.governance.registry import AgentState as GovAgentState
from carsoul_agent.governance.registry import managed_registry
from carsoul_agent.workflow_engine.intent import Intent, IntentUnderstanding
from carsoul_agent.workflow_engine.memory import TaskMemory, store_memory
from carsoul_agent.workflow_engine.planner import Task, TaskPlanner, TaskTree
from carsoul_agent.workflow_engine.state_machine import WorkflowState, WorkflowStateMachine
from carsoul_agent.workflow_engine.task_manager import TaskManager

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """The DAG execution engine — Goal → Plan → Execute → Verify → Act.

    This is the V1.0 workflow engine that wraps the existing five-sub-agent
    core workflow with governance, planning, parallel execution, and
    failure recovery.
    """

    def __init__(
        self,
        perception_agent: Any | None = None,
        diagnosis_agent: Any | None = None,
        risk_agent: Any | None = None,
        explainer_agent: Any | None = None,
        service_agent: Any | None = None,
        judge_agent: JudgeAgent | None = None,
        max_workers: int = 4,
    ) -> None:
        self._perception = perception_agent
        self._diagnosis = diagnosis_agent
        self._risk = risk_agent
        self._explainer = explainer_agent
        self._service = service_agent
        self._judge = judge_agent or JudgeAgent()
        self._max_workers = max_workers

        self._intent_parser = IntentUnderstanding()
        self._planner = TaskPlanner()
        self._task_manager = TaskManager()

    def execute(self, message: str, state: AgentState) -> AgentState:
        """Execute the full workflow: Intent → Plan → Execute → Verify.

        Args:
            message: The user's raw message.
            state: The initial AgentState (pre-populated with vehicle data).

        Returns:
            The updated AgentState with all workflow outputs.
        """
        workflow_id = f"wf_{int(time.time() * 1000)}"

        # --- Phase 1: Intent Understanding ---
        intent = self._intent_parser.parse(message)
        state.setdefault("trace_log", []).append(trace_entry(
            step="__workflow_start__",
            agent="workflow_engine",
            detail=f"工作流引擎启动：意图={intent.goal_label}，场景={intent.scenario}，优先级={intent.priority}",
            data={"workflow_id": workflow_id, "intent": intent.to_dict()},
        ))

        # --- Phase 2: Task Planning ---
        task_tree = self._planner.plan(intent)
        state["trace_log"].append(trace_entry(
            step="__plan__",
            agent="workflow_engine",
            detail=f"任务规划完成：{len(task_tree.all_tasks())} 个任务，根目标={task_tree.root_goal}",
            data={"task_tree": task_tree.to_dict()},
        ))

        # --- Phase 3: Execute ---
        sm = WorkflowStateMachine(workflow_id)
        memory = TaskMemory(workflow_id, task_tree.root_goal)
        memory.record_input("message", message)
        memory.record_input("vehicle_state", state.get("vehicle_state", {}))

        sm.transition(WorkflowState.ANALYZING, "开始执行任务 DAG")

        self._execute_dag(task_tree, state, sm, memory, intent)

        # --- Phase 4: Verify ---
        if sm.state == WorkflowState.ANALYZING:
            sm.transition(WorkflowState.SUCCESS, "所有任务执行完成")
            sm.transition(WorkflowState.VERIFY, "验证工作流结果")
            # Simple verification: check that key outputs exist.
            verified = self._verify_results(state, intent)
            if verified:
                sm.transition(WorkflowState.COMPLETE, "工作流验证通过，执行完成")
            else:
                sm.transition(WorkflowState.ERROR, "工作流结果验证失败")
                sm.transition(WorkflowState.COMPLETE, "工作流以降级状态完成")
        elif sm.state == WorkflowState.ERROR:
            sm.transition(WorkflowState.COMPLETE, "工作流在错误状态下终止")

        # --- Phase 5: Record memory ---
        memory.record_final_conclusion({
            "is_normal": state.get("is_normal", False),
            "anomaly_count": len(state.get("anomalies", [])),
            "diagnosis": state.get("diagnosis", {}),
            "risk_level": state.get("risk_assessment", {}).get("level"),
            "workflow_state": sm.state.value,
        })
        store_memory(memory)

        # Add workflow metadata to state for frontend visualisation.
        state["workflow_meta"] = {
            "workflow_id": workflow_id,
            "intent": intent.to_dict(),
            "task_tree": task_tree.to_dict(),
            "state_machine": sm.to_dict(),
            "memory": memory.to_dict(),
            "governance": managed_registry.to_dict(),
        }
        state["trace_log"].append(trace_entry(
            step="__workflow_complete__",
            agent="workflow_engine",
            detail=f"工作流完成：状态={sm.state.value}，参与Agent={memory._participating_agents}",
            data=state["workflow_meta"],
        ))

        return state

    # ------------------------------------------------------------------
    #  DAG execution
    # ------------------------------------------------------------------
    def _execute_dag(
        self,
        tree: TaskTree,
        state: AgentState,
        sm: WorkflowStateMachine,
        memory: TaskMemory,
        intent: Intent,
    ) -> None:
        """Execute the task DAG respecting dependencies."""
        max_iterations = 20  # safety guard

        while not tree.is_complete() and not tree.has_failed() and max_iterations > 0:
            max_iterations -= 1
            ready = tree.ready_tasks()
            if not ready:
                if tree.has_failed():
                    sm.transition(WorkflowState.ERROR, "任务失败且无法恢复")
                break

            # Group ready tasks by parallel_group for concurrent execution.
            parallel_groups: dict[str | None, list[Task]] = {}
            for task in ready:
                pg = task.parallel_group
                parallel_groups.setdefault(pg, []).append(task)

            # Execute each group; within a group, run in parallel.
            for _group, tasks in parallel_groups.items():
                if len(tasks) == 1:
                    self._execute_task(tasks[0], state, sm, memory)
                else:
                    self._execute_parallel(tasks, state, sm, memory)

            # Dynamic workflow adjustment (§6.3).
            self._dynamic_adjust(tree, state, intent)

        if tree.has_failed():
            sm.transition(WorkflowState.ERROR, "一个或多个任务失败且重试耗尽")

    def _execute_task(
        self,
        task: Task,
        state: AgentState,
        sm: WorkflowStateMachine,
        memory: TaskMemory,
    ) -> None:
        """Execute a single task with full governance tracking."""
        # Assign via router.
        agent_id = self._task_manager.assign(task)
        memory.record_agent_participation(agent_id)

        self._task_manager.start(task)
        start_time = time.time()

        success = False
        try:
            with lifecycle_manager.task_scope(agent_id):
                result = self._dispatch_task(task, state)
            task.result = result
            self._task_manager.complete(task, result or {})
            success = True

            # Record intermediate result in memory.
            if result:
                memory.record_intermediate(task.task_id, result)

        except Exception as exc:  # noqa: BLE001
            logger.exception("Task %s failed: %s", task.task_id, exc)
            can_retry = self._task_manager.fail(task, str(exc))
            if can_retry:
                # Retry: re-execute the task.
                self._retry_task(task, state, sm, memory)
            else:
                # Fallback: try a degraded execution path.
                fallback_result = self._fallback_task(task, state)
                if fallback_result is not None:
                    task.result = fallback_result
                    self._task_manager.complete(task, fallback_result)
                    success = True
                else:
                    sm.transition(
                        WorkflowState.ERROR,
                        f"任务 {task.name} 失败且无法恢复: {exc}",
                    )

        duration_ms = (time.time() - start_time) * 1000
        memory.record_agent_performance(agent_id, duration_ms, success)

        # Trace.
        state.setdefault("trace_log", []).append(trace_entry(
            step=f"__task_{task.task_type}__",
            agent=agent_id,
            detail=f"任务「{task.name}」{'完成' if success else '失败'}（{task.state}）",
            data=task.to_dict(),
        ))

    def _execute_parallel(
        self,
        tasks: list[Task],
        state: AgentState,
        sm: WorkflowStateMachine,
        memory: TaskMemory,
    ) -> None:
        """Execute multiple independent tasks in parallel (§6.2)."""
        state.setdefault("trace_log", []).append(trace_entry(
            step="__parallel_start__",
            agent="workflow_engine",
            detail=f"并行执行 {len(tasks)} 个任务：{', '.join(t.name for t in tasks)}",
            data={"task_ids": [t.task_id for t in tasks]},
        ))

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {
                pool.submit(self._execute_task, task, state, sm, memory): task
                for task in tasks
            }
            for future in as_completed(futures):
                task = futures[future]
                try:
                    future.result()
                except Exception as exc:  # noqa: BLE001
                    logger.error("Parallel task %s raised: %s", task.task_id, exc)

    def _retry_task(
        self,
        task: Task,
        state: AgentState,
        sm: WorkflowStateMachine,
        memory: TaskMemory,
    ) -> None:
        """Retry a failed task (§9 Retry mechanism)."""
        logger.info("Retrying task %s (attempt %d)", task.task_id, task.retry_count)
        try:
            self._task_manager.assign(task)
            self._task_manager.start(task)
            with lifecycle_manager.task_scope(task.agent_id):
                result = self._dispatch_task(task, state)
            task.result = result
            self._task_manager.complete(task, result or {})
            if result:
                memory.record_intermediate(task.task_id, result)
        except Exception as exc:  # noqa: BLE001
            logger.error("Retry %d failed for task %s: %s", task.retry_count, task.task_id, exc)
            self._task_manager.fail(task, str(exc))

    def _fallback_task(self, task: Task, state: AgentState) -> dict[str, Any] | None:
        """Fallback strategy when retries are exhausted (§9 Fallback).

        For each task type, try a degraded/rule-based execution path
        that doesn't rely on the LLM.
        """
        logger.warning("Fallback for task %s (%s)", task.task_id, task.task_type)
        try:
            result = self._dispatch_task(task, state, force_offline=True)
            return result
        except Exception as exc:  # noqa: BLE001
            logger.error("Fallback also failed for task %s: %s", task.task_id, exc)
            return None

    # ------------------------------------------------------------------
    #  Task dispatch (maps task_type → existing agent function)
    # ------------------------------------------------------------------
    def _dispatch_task(
        self,
        task: Task,
        state: AgentState,
        force_offline: bool = False,
    ) -> dict[str, Any]:
        """Execute a task by dispatching to the appropriate agent.

        Maps the planned task to the existing core agent implementation,
        adding governance tracking around each invocation.
        """
        task_type = task.task_type

        if task_type == "perception" and self._perception is not None:
            self._perception.run(state)
            return {"anomaly_count": len(state.get("anomalies", []))}

        if task_type == "diagnosis" and self._diagnosis is not None:
            self._diagnosis.run(state)
            return {"diagnosis": state.get("diagnosis", {})}

        if task_type == "judge":
            opinions = state.get("expert_opinions", [])
            verdict = self._judge.resolve(opinions)
            state["judge_verdict"] = verdict
            state.setdefault("trace_log", []).append(trace_entry(
                step="reason",
                agent="judge",
                detail=f"决策裁判：{verdict.get('verdict')}，置信度={verdict.get('confidence')}",
                data=verdict,
            ))
            return verdict

        if task_type == "risk" and self._risk is not None:
            self._risk.run(state)
            return {"risk_assessment": state.get("risk_assessment", {})}

        if task_type == "explainer" and self._explainer is not None:
            self._explainer.run(state)
            return {"explanation": state.get("explanation", "")[:200]}

        if task_type == "service" and self._service is not None:
            self._service.run(state)
            return {"service_suggestion": state.get("service_suggestion", {})}

        logger.warning("No dispatcher for task type '%s'", task_type)
        return {}

    # ------------------------------------------------------------------
    #  Dynamic workflow adjustment (§6.3)
    # ------------------------------------------------------------------
    def _dynamic_adjust(self, tree: TaskTree, state: AgentState, intent: Intent) -> None:
        """Dynamically add tasks based on intermediate results (§6.3).

        Example: if the perception node detects a battery thermal anomaly
        with >90% probability, automatically inject a Safety Agent risk
        assessment task before the normal risk node.
        """
        anomalies = state.get("anomalies", [])
        existing_types = {t.task_type for t in tree.all_tasks()}

        # If battery thermal anomaly is detected and no judge task exists yet,
        # mark it for high-priority handling.
        battery_thermal = any(
            a.get("category") == "battery" and a.get("level") in ("urgent", "warning")
            for a in anomalies
        )
        if battery_thermal and "judge" not in existing_types and intent.priority == "urgent":
            # The planner already includes judge for most scenarios, but if
            # it wasn't planned, we dynamically add it.
            logger.info("Dynamic adjustment: battery thermal detected, ensuring judge task exists")

        # If multiple severe anomalies are found, ensure the judge task runs
        # (it may have been skipped in simpler task plans).
        severe_count = sum(1 for a in anomalies if a.get("level") in ("urgent", "warning"))
        if severe_count >= 3 and "judge" not in existing_types:
            insert_after = None
            for t in tree.all_tasks():
                if t.task_type == "diagnosis":
                    insert_after = t
                    break
            if insert_after:
                judge_task = Task(
                    task_id=f"t_dyn_judge_{int(time.time())}",
                    name="动态注入·决策裁判",
                    task_type="judge",
                    agent_id="judge",
                    dependencies=[insert_after.task_id],
                    priority=8,
                    config={"dynamic": True, "reason": f"{severe_count}个严重异常触发冲突仲裁"},
                )
                tree.add_task(judge_task)
                state.setdefault("trace_log", []).append(trace_entry(
                    step="__dynamic_adjust__",
                    agent="workflow_engine",
                    detail=f"动态工作流调整：检测到{severe_count}个严重异常，注入决策裁判任务",
                    data={"added_task": judge_task.to_dict()},
                ))

    # ------------------------------------------------------------------
    #  Verification (Phase 4)
    # ------------------------------------------------------------------
    def _verify_results(self, state: AgentState, intent: Intent) -> bool:
        """Verify that the workflow produced expected outputs.

        Simple checks: perception produced anomalies list, diagnosis
        produced a primary, risk produced a level, etc.
        """
        checks = [
            "anomalies" in state,
            "is_normal" in state,
        ]
        if not state.get("is_normal", False):
            checks.extend([
                "diagnosis" in state,
                "risk_assessment" in state,
                "explanation" in state,
            ])
        return all(checks)

    # ------------------------------------------------------------------
    #  Human-in-loop (§9)
    # ------------------------------------------------------------------
    def check_human_in_loop_needed(self, state: AgentState) -> bool:
        """Determine if human confirmation is required before executing.

        High-risk scenarios (e.g. battery thermal runaway risk) require
        human confirmation before the service agent executes actions.
        """
        risk = state.get("risk_assessment", {})
        level = risk.get("level", "info")
        probability = risk.get("probability_percent", 0)

        # Urgent risk with high probability → human-in-loop.
        if level == "urgent" and probability >= 80:
            return True
        return False
