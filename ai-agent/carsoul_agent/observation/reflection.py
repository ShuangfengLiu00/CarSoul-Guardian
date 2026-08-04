"""Reflection Engine — Agent 反思引擎.

Implements Module 02 of the Agent Evolution Engine:
类似人类的"复盘能力"，每次任务结束后自动启动 Reflection Agent。

分析三个层次：
  - 任务层：目标是否完成？是否解决用户问题？
  - 推理层：是否调用正确Agent？是否缺少数据？是否存在错误判断？
  - 结果层：预测是否准确？用户是否满意？

输出 Reflection Report：
  Task: Battery Diagnosis
  Success: YES
  Weakness: 没有考虑环境温度
  Improvement: 增加Weather Factor
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ReflectionReport:
    """单次任务的反思报告."""

    reflection_id: str
    task_id: str
    agent_id: str
    task_type: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    # ---- 任务层 ----
    task_success: bool = False  # 目标是否完成
    user_problem_solved: bool = False  # 是否解决用户问题
    # ---- 推理层 ----
    correct_agent_called: bool = True  # 是否调用了正确的Agent
    missing_data: list[str] = field(default_factory=list)  # 缺少的数据
    reasoning_errors: list[str] = field(default_factory=list)  # 推理错误
    # ---- 结果层 ----
    prediction_accurate: bool = True  # 预测是否准确
    user_satisfied: bool = True  # 用户是否满意
    # ---- 综合分析 ----
    strengths: list[str] = field(default_factory=list)  # 做得好的地方
    weaknesses: list[str] = field(default_factory=list)  # 不足之处
    improvements: list[str] = field(default_factory=list)  # 改进建议
    new_knowledge: str = ""  # 是否产生新知识
    # ---- 改进优先级 ----
    improvement_priority: str = "low"  # low / medium / high
    # ---- 关联数据 ----
    evaluation_id: str = ""  # 关联的评估记录ID
    trace_id: str = ""  # 关联的追踪记录ID

    def to_dict(self) -> dict[str, Any]:
        return {
            "reflection_id": self.reflection_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "timestamp": self.timestamp,
            "task_layer": {
                "task_success": self.task_success,
                "user_problem_solved": self.user_problem_solved,
            },
            "reasoning_layer": {
                "correct_agent_called": self.correct_agent_called,
                "missing_data": self.missing_data,
                "reasoning_errors": self.reasoning_errors,
            },
            "result_layer": {
                "prediction_accurate": self.prediction_accurate,
                "user_satisfied": self.user_satisfied,
            },
            "analysis": {
                "strengths": self.strengths,
                "weaknesses": self.weaknesses,
                "improvements": self.improvements,
                "new_knowledge": self.new_knowledge,
            },
            "improvement_priority": self.improvement_priority,
            "evaluation_id": self.evaluation_id,
            "trace_id": self.trace_id,
        }


class ReflectionEngine:
    """Agent 反思引擎 — 每次任务结束后自动复盘.

    工作流程：
      1. reflect: 接收任务执行数据，生成反思报告
      2. 自动分析任务层/推理层/结果层
      3. 提取改进建议与新知识
      4. 反馈给 Experience Miner 和 Skill Evolution
    """

    def __init__(self) -> None:
        self._reports: list[ReflectionReport] = []
        # agent_id → list of weakness 标签，用于跨任务模式识别
        self._weakness_tracker: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    #  Reflection — 反思执行
    # ------------------------------------------------------------------
    def reflect(
        self,
        task_id: str,
        agent_id: str,
        task_type: str,
        task_success: bool,
        user_problem_solved: bool = True,
        correct_agent_called: bool = True,
        missing_data: list[str] | None = None,
        reasoning_errors: list[str] | None = None,
        prediction_accurate: bool = True,
        user_satisfied: bool = True,
        evaluation_id: str = "",
        trace_id: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> ReflectionReport:
        """对一次任务执行进行反思，生成反思报告.

        Args:
            task_id: 任务ID
            agent_id: 执行Agent ID
            task_type: 任务类型
            task_success: 任务是否成功
            user_problem_solved: 是否解决了用户问题
            correct_agent_called: 是否调用了正确的Agent
            missing_data: 缺少的数据列表
            reasoning_errors: 推理错误列表
            prediction_accurate: 预测是否准确
            user_satisfied: 用户是否满意
            evaluation_id: 关联的评估记录ID
            trace_id: 关联的追踪记录ID
            extra_context: 额外上下文数据

        Returns:
            生成的 ReflectionReport
        """
        report = ReflectionReport(
            reflection_id=f"refl_{uuid.uuid4().hex[:12]}",
            task_id=task_id,
            agent_id=agent_id,
            task_type=task_type,
            task_success=task_success,
            user_problem_solved=user_problem_solved,
            correct_agent_called=correct_agent_called,
            missing_data=missing_data or [],
            reasoning_errors=reasoning_errors or [],
            prediction_accurate=prediction_accurate,
            user_satisfied=user_satisfied,
            evaluation_id=evaluation_id,
            trace_id=trace_id,
        )
        # 自动分析优缺点和改进建议
        self._analyze(report, extra_context or {})
        # 确定改进优先级
        self._assess_priority(report)
        self._reports.append(report)
        # 更新弱点追踪器
        if report.weaknesses:
            self._weakness_tracker.setdefault(agent_id, []).extend(report.weaknesses)
        logger.info(
            "Reflection completed: %s (agent=%s, success=%s, priority=%s)",
            report.reflection_id, agent_id, task_success, report.improvement_priority,
        )
        return report

    def _analyze(
        self,
        report: ReflectionReport,
        context: dict[str, Any],
    ) -> None:
        """自动分析优缺点和改进建议."""
        # ---- 优点 ----
        if report.task_success:
            report.strengths.append("任务成功完成")
        if report.user_problem_solved:
            report.strengths.append("有效解决用户问题")
        if report.correct_agent_called:
            report.strengths.append("Agent 调用正确")
        if report.prediction_accurate:
            report.strengths.append("预测准确")
        if report.user_satisfied:
            report.strengths.append("用户满意")

        # ---- 不足 ----
        if not report.task_success:
            report.weaknesses.append("任务未成功完成")
        if not report.user_problem_solved:
            report.weaknesses.append("未完全解决用户问题")
        if not report.correct_agent_called:
            report.weaknesses.append("调用了错误的Agent")
        if report.missing_data:
            report.weaknesses.append(f"缺少关键数据: {', '.join(report.missing_data)}")
        if report.reasoning_errors:
            report.weaknesses.append(f"推理存在错误: {', '.join(report.reasoning_errors)}")
        if not report.prediction_accurate:
            report.weaknesses.append("预测不准确")
        if not report.user_satisfied:
            report.weaknesses.append("用户不满意")

        # ---- 改进建议 ----
        if report.missing_data:
            for data in report.missing_data:
                report.improvements.append(f"增加 {data} 数据采集")
        if report.reasoning_errors:
            report.improvements.append("优化推理逻辑，减少错误判断")
        if not report.correct_agent_called:
            report.improvements.append("改进 Agent 路由策略，确保调用正确Agent")
        if not report.prediction_accurate:
            report.improvements.append("引入更多特征因素提升预测精度")
        if not report.user_satisfied:
            report.improvements.append("优化响应语气与结构，提升用户体验")

        # ---- 新知识 ----
        if context.get("discovered_pattern"):
            report.new_knowledge = context["discovered_pattern"]
        elif report.missing_data:
            report.new_knowledge = f"发现 {report.task_type} 需要额外考虑: {', '.join(report.missing_data)}"

    def _assess_priority(self, report: ReflectionReport) -> None:
        """根据不足数量和严重程度评估改进优先级."""
        weakness_count = len(report.weaknesses)
        if not report.task_success or weakness_count >= 3:
            report.improvement_priority = "high"
        elif weakness_count >= 1 or not report.prediction_accurate:
            report.improvement_priority = "medium"
        else:
            report.improvement_priority = "low"

    # ------------------------------------------------------------------
    #  Query
    # ------------------------------------------------------------------
    def get_agent_reflections(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """返回某 Agent 的反思历史（newest first）."""
        reports = [r for r in self._reports if r.agent_id == agent_id]
        return [r.to_dict() for r in reversed(reports[-limit:])]

    def get_recent_reflections(self, limit: int = 20) -> list[dict[str, Any]]:
        """返回最近的反思报告."""
        return [r.to_dict() for r in reversed(self._reports[-limit:])]

    def get_reflection(self, reflection_id: str) -> dict[str, Any] | None:
        """返回指定反思报告."""
        for report in self._reports:
            if report.reflection_id == reflection_id:
                return report.to_dict()
        return None

    def get_agent_weaknesses(self, agent_id: str) -> dict[str, Any]:
        """返回某 Agent 的弱点模式分析."""
        weaknesses = self._weakness_tracker.get(agent_id, [])
        if not weaknesses:
            return {"agent_id": agent_id, "weakness_count": 0, "patterns": {}}
        # 统计弱点频次
        from collections import Counter
        counts = Counter(weaknesses)
        return {
            "agent_id": agent_id,
            "weakness_count": len(weaknesses),
            "top_weaknesses": counts.most_common(5),
        }

    def get_summary(self) -> dict[str, Any]:
        """反思引擎摘要."""
        total = len(self._reports)
        success_count = sum(1 for r in self._reports if r.task_success)
        high_priority = sum(1 for r in self._reports if r.improvement_priority == "high")
        return {
            "total_reflections": total,
            "success_rate": round(success_count / total, 4) if total else 0.0,
            "high_priority_count": high_priority,
            "agents_reflected": len({r.agent_id for r in self._reports}),
            "recent_reflections": [r.to_dict() for r in self._reports[-10:]],
        }

    def to_dict(self) -> dict[str, Any]:
        """整体快照."""
        return {
            "summary": self.get_summary(),
        }


# Singleton instance.
reflection_engine = ReflectionEngine()
