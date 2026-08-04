"""Evolution Engine — 进化引擎完整闭环编排器.

Implements the complete Evolution Workflow from the design doc:

    用户提出问题 → Manager Agent拆解 → 多个专业Agent执行
    → 产生结果 → Evaluation Agent评分 → Reflection Agent复盘
    → Experience Miner提取经验 → Knowledge更新
    → Skill Evolution判断 → 生成新版本Skill → 部署 → 下一次任务使用

形成 Experience → Knowledge → Skill → Intelligence 永续循环。

本模块编排所有进化子引擎：
  - Experience Miner (experience.py)
  - Reflection Engine (reflection.py)
  - Skill Evolution Engine (skill_evolution.py)
  - Evaluation Engine (evaluation.py)
  - Optimization Loop (optimization.py)
  - Evolution Manager (evolution.py)
  + Memory layers (episodic / skill / evolution memory)
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EvolutionCycleResult:
    """一次完整进化闭环的执行结果."""

    cycle_id: str
    started_at: str
    completed_at: str = ""
    # 各阶段结果
    evaluation: dict[str, Any] = field(default_factory=dict)
    reflection: dict[str, Any] = field(default_factory=dict)
    experience: dict[str, Any] = field(default_factory=dict)
    skill_evolution: dict[str, Any] = field(default_factory=dict)
    optimization: dict[str, Any] = field(default_factory=dict)
    # 总结
    skills_evolved: list[str] = field(default_factory=list)
    experiences_mined: int = 0
    patterns_discovered: int = 0
    improvements_generated: int = 0
    success: bool = True
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "evaluation": self.evaluation,
            "reflection": self.reflection,
            "experience": self.experience,
            "skill_evolution": self.skill_evolution,
            "optimization": self.optimization,
            "skills_evolved": self.skills_evolved,
            "experiences_mined": self.experiences_mined,
            "patterns_discovered": self.patterns_discovered,
            "improvements_generated": self.improvements_generated,
            "success": self.success,
            "summary": self.summary,
        }


class EvolutionEngine:
    """进化引擎编排器 — 串联所有进化子引擎形成完整闭环.

    完整闭环流程（run_evolution_cycle）：
      Step 1: 采集评估数据 (Evaluation Engine)
      Step 2: 执行反思 (Reflection Engine)
      Step 3: 挖掘经验 (Experience Miner)
      Step 4: 检测并执行技能进化 (Skill Evolution Engine)
      Step 5: 生成优化建议 (Optimization Loop)
      Step 6: 记录进化里程碑 (Evolution Memory)
      Step 7: 生成总结报告
    """

    def __init__(self) -> None:
        self._cycles: list[EvolutionCycleResult] = []
        self._enabled: bool = True

    # ------------------------------------------------------------------
    #  Task-level integration — 任务级进化钩子
    # ------------------------------------------------------------------
    def on_task_completed(
        self,
        task_id: str,
        agent_id: str,
        task_type: str,
        problem: str,
        solution: str,
        result: str,
        task_success: bool = True,
        user_satisfied: bool = True,
        prediction_accurate: bool = True,
        vehicle_id: str = "",
        missing_data: list[str] | None = None,
        reasoning_errors: list[str] | None = None,
        source_data: dict[str, Any] | None = None,
        pattern_tags: list[str] | None = None,
        evaluation_metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """任务完成后触发的完整进化钩子.

        这是最核心的集成方法 — 每次Agent任务完成后调用，自动执行：
          1. 记录评估数据
          2. 执行反思
          3. 提取经验
          4. 记忆存储
          5. 检测技能进化需求

        Args:
            task_id: 任务ID
            agent_id: 执行Agent ID
            task_type: 任务类型
            problem: 问题描述
            solution: 解决方案
            result: 执行结果
            task_success: 任务是否成功
            user_satisfied: 用户是否满意
            prediction_accurate: 预测是否准确
            vehicle_id: 车辆ID
            missing_data: 缺失数据列表
            reasoning_errors: 推理错误列表
            source_data: 溯源数据
            pattern_tags: 模式标签
            evaluation_metrics: 评估指标

        Returns:
            进化钩子执行结果摘要
        """
        results: dict[str, Any] = {"task_id": task_id, "agent_id": agent_id}

        # Step 1: 记录评估
        try:
            from carsoul_agent.observation.evaluation import evaluation_engine
            eval_record = evaluation_engine.evaluate(
                agent_id=agent_id,
                workflow_id=task_id,
                accuracy=evaluation_metrics.get("accuracy", 0.85 if task_success else 0.5) if evaluation_metrics else (0.85 if task_success else 0.5),
                user_satisfaction=0.9 if user_satisfied else 0.4,
                risk_accuracy=evaluation_metrics.get("risk_accuracy", 0.8) if evaluation_metrics else 0.8,
                token_consumed=evaluation_metrics.get("token_consumed", 0) if evaluation_metrics else 0,
                duration_ms=evaluation_metrics.get("duration_ms", 0) if evaluation_metrics else 0,
                error_count=evaluation_metrics.get("error_count", 0) if evaluation_metrics else 0,
            )
            results["evaluation_id"] = eval_record.evaluation_id
        except Exception as exc:  # noqa: BLE001
            logger.debug("evaluation skipped: %s", exc)

        # Step 2: 执行反思
        try:
            from carsoul_agent.observation.reflection import reflection_engine
            refl_report = reflection_engine.reflect(
                task_id=task_id,
                agent_id=agent_id,
                task_type=task_type,
                task_success=task_success,
                user_problem_solved=task_success,
                correct_agent_called=True,
                missing_data=missing_data,
                reasoning_errors=reasoning_errors,
                prediction_accurate=prediction_accurate,
                user_satisfied=user_satisfied,
                evaluation_id=results.get("evaluation_id", ""),
            )
            results["reflection_id"] = refl_report.reflection_id
            results["improvements"] = refl_report.improvements
        except Exception as exc:  # noqa: BLE001
            logger.debug("reflection skipped: %s", exc)

        # Step 3: 提取经验
        try:
            from carsoul_agent.observation.experience import experience_miner
            exp_case = experience_miner.record_execution(
                task_type=task_type,
                problem=problem,
                solution=solution,
                result=result,
                success=task_success,
                vehicle_id=vehicle_id,
                agent_id=agent_id,
                source_data=source_data,
                pattern_tags=pattern_tags,
            )
            results["experience_case_id"] = exp_case.case_id
        except Exception as exc:  # noqa: BLE001
            logger.debug("experience mining skipped: %s", exc)

        # Step 4: 记忆存储
        try:
            from carsoul_agent.memory.episodic import episodic_memory
            from carsoul_agent.memory.skill_memory import skill_memory
            from carsoul_agent.memory.evolution_memory import evolution_memory
            # 情景记忆
            episodic_memory.record_episode(
                vehicle_id=vehicle_id,
                task_type=task_type,
                event_description=problem,
                outcome=result,
                agent_id=agent_id,
                importance_score=0.8 if task_success else 0.5,
                related_data={
                    "solution": solution,
                    "success": task_success,
                    "task_id": task_id,
                },
            )
            # 技能执行记忆
            skill_memory.record_execution(
                skill_id=task_type,
                skill_version="v1.0",
                agent_id=agent_id,
                task_id=task_id,
                success=task_success,
                execution_time_ms=evaluation_metrics.get("duration_ms", 0) if evaluation_metrics else 0,
                result_summary=result,
            )
            results["memory_stored"] = True
        except Exception as exc:  # noqa: BLE001
            logger.debug("memory storage skipped: %s", exc)

        # Step 5: 检测技能进化需求（非阻塞）
        try:
            from carsoul_agent.observation.skill_evolution import skill_evolution_engine
            detection = skill_evolution_engine.detect_mutation_need(agent_id)
            results["mutation_needed"] = detection.get("needed", False)
            if detection.get("needed"):
                results["mutation_reasons"] = detection.get("reasons", [])
        except Exception as exc:  # noqa: BLE001
            logger.debug("skill evolution check skipped: %s", exc)

        logger.info(
            "Evolution hook completed for task %s (agent=%s, success=%s)",
            task_id, agent_id, task_success,
        )
        return results

    # ------------------------------------------------------------------
    #  Full Evolution Cycle — 完整进化闭环
    # ------------------------------------------------------------------
    def run_evolution_cycle(self) -> EvolutionCycleResult:
        """执行一次完整的进化闭环.

        定期（如每天凌晨）运行，对整个Agent舰队执行：
          1. 采集评估数据
          2. 执行批量反思
          3. 挖掘经验模式
          4. 自动进化技能
          5. 生成优化建议
          6. 记录进化里程碑
        """
        cycle_id = f"cycle_{uuid.uuid4().hex[:12]}"
        started_at = datetime.now(timezone.utc).isoformat()
        result = EvolutionCycleResult(cycle_id=cycle_id, started_at=started_at)
        logger.info("Evolution cycle started: %s", cycle_id)

        # Step 1: 采集评估数据
        try:
            from carsoul_agent.observation.evaluation import evaluation_engine
            result.evaluation = evaluation_engine.get_fleet_evaluation()
        except Exception as exc:  # noqa: BLE001
            logger.warning("evaluation step failed: %s", exc)

        # Step 2: 执行优化分析（Collect → Analyze → Evaluate → Optimize）
        try:
            from carsoul_agent.observation.optimization import optimization_loop
            actions = optimization_loop.run_cycle()
            result.optimization = {
                "generated_actions": len(actions),
                "actions": [a.to_dict() for a in actions[:10]],
            }
            result.improvements_generated = len(actions)
        except Exception as exc:  # noqa: BLE001
            logger.warning("optimization step failed: %s", exc)

        # Step 3: 挖掘经验模式
        try:
            from carsoul_agent.observation.experience import experience_miner
            summary = experience_miner.get_summary()
            result.experience = summary
            result.experiences_mined = summary.get("total_cases", 0)
            result.patterns_discovered = summary.get("total_patterns", 0)
        except Exception as exc:  # noqa: BLE001
            logger.warning("experience mining step failed: %s", exc)

        # Step 4: 反思摘要
        try:
            from carsoul_agent.observation.reflection import reflection_engine
            result.reflection = reflection_engine.get_summary()
        except Exception as exc:  # noqa: BLE001
            logger.warning("reflection step failed: %s", exc)

        # Step 5: 自动进化技能
        try:
            from carsoul_agent.observation.skill_evolution import skill_evolution_engine
            from carsoul_agent.governance.skill_registry import (
                skill_registry,
                register_governance_skills,
            )
            if not skill_registry.all_skills():
                register_governance_skills()
            # 对每个技能检测进化需求
            evolved_skills: list[str] = []
            evolution_results: list[dict[str, Any]] = []
            for skill in skill_registry.all_skills():
                detection = skill_evolution_engine.detect_mutation_need(skill.skill_id)
                if detection.get("needed"):
                    evo_result = skill_evolution_engine.auto_evolve_skill(skill.skill_id)
                    evolution_results.append(evo_result)
                    if evo_result.get("evolved"):
                        evolved_skills.append(skill.skill_id)
            result.skill_evolution = {
                "skills_checked": len(skill_registry.all_skills()),
                "skills_needing_evolution": len(evolution_results),
                "skills_evolved": evolved_skills,
                "details": evolution_results,
            }
            result.skills_evolved = evolved_skills
        except Exception as exc:  # noqa: BLE001
            logger.warning("skill evolution step failed: %s", exc)

        # Step 6: 记录进化里程碑
        try:
            from carsoul_agent.memory.evolution_memory import evolution_memory
            if result.skills_evolved or result.patterns_discovered:
                evolution_memory.record_milestone(
                    agent_id="system",
                    milestone_type="skill_evolution" if result.skills_evolved else "experience_discovery",
                    description=(
                        f"进化周期 {cycle_id}: "
                        f"进化{len(result.skills_evolved)}个技能, "
                        f"发现{result.patterns_discovered}个经验模式, "
                        f"生成{result.improvements_generated}个优化建议"
                    ),
                    before_state={
                        "skills_checked": result.skill_evolution.get("skills_checked", 0),
                    },
                    after_state={
                        "skills_evolved": result.skills_evolved,
                        "patterns_discovered": result.patterns_discovered,
                        "improvements_generated": result.improvements_generated,
                    },
                    impact_metrics={
                        "evolution_count": len(result.skills_evolved),
                        "experience_count": result.experiences_mined,
                    },
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("milestone recording failed: %s", exc)

        # Step 7: 生成总结
        result.completed_at = datetime.now(timezone.utc).isoformat()
        result.summary = self._generate_summary(result)
        result.success = True
        self._cycles.append(result)
        logger.info(
            "Evolution cycle completed: %s (evolved=%d, patterns=%d, improvements=%d)",
            cycle_id, len(result.skills_evolved),
            result.patterns_discovered, result.improvements_generated,
        )
        return result

    def _generate_summary(self, result: EvolutionCycleResult) -> str:
        """生成进化周期的自然语言总结."""
        parts: list[str] = []
        parts.append(f"进化周期 {result.cycle_id} 完成。")
        if result.skills_evolved:
            parts.append(f"成功进化 {len(result.skills_evolved)} 个技能: {', '.join(result.skills_evolved)}。")
        if result.patterns_discovered:
            parts.append(f"发现 {result.patterns_discovered} 个经验模式。")
        if result.improvements_generated:
            parts.append(f"生成 {result.improvements_generated} 个优化建议。")
        if not any([result.skills_evolved, result.patterns_discovered, result.improvements_generated]):
            parts.append("本周期无需进化，系统运行稳定。")
        return " ".join(parts)

    # ------------------------------------------------------------------
    #  Demo: Seed evolution data — 演示数据注入
    # ------------------------------------------------------------------
    def seed_demo_data(self) -> dict[str, Any]:
        """注入演示数据，展示进化引擎效果.

        模拟文档中描述的场景：
          - 多次电池诊断任务 → 发现冬季续航下降模式
          - 反思发现缺少温度因素
          - 技能从V1.0进化到V1.1
        """
        results: dict[str, Any] = {"seeded": []}

        # 模拟多次电池诊断任务（冬季续航下降场景）
        winter_cases = [
            {
                "problem": "冬季续航下降20%",
                "solution": "检查胎压并调整至2.5bar",
                "result": "续航恢复12%",
                "tags": ["winter", "range_loss", "tire_pressure"],
                "data": {"temperature": "-2℃", "tire_pressure": "2.1bar", "soc": "65%"},
            },
            {
                "problem": "冬季续航下降15%",
                "solution": "检查胎压并调整至2.5bar",
                "result": "续航恢复10%",
                "tags": ["winter", "range_loss", "tire_pressure"],
                "data": {"temperature": "1℃", "tire_pressure": "2.2bar", "soc": "70%"},
            },
            {
                "problem": "冬季续航下降25%",
                "solution": "检查胎压并调整至2.5bar",
                "result": "续航恢复15%",
                "tags": ["winter", "range_loss", "tire_pressure"],
                "data": {"temperature": "-5℃", "tire_pressure": "2.0bar", "soc": "60%"},
            },
            {
                "problem": "冬季续航下降18%",
                "solution": "检查胎压并调整至2.5bar",
                "result": "续航恢复11%",
                "tags": ["winter", "range_loss", "tire_pressure"],
                "data": {"temperature": "0℃", "tire_pressure": "2.1bar", "soc": "68%"},
            },
        ]

        try:
            from carsoul_agent.observation.experience import experience_miner
            from carsoul_agent.observation.reflection import reflection_engine
            from carsoul_agent.observation.skill_evolution import skill_evolution_engine
            from carsoul_agent.observation.evaluation import evaluation_engine
            from carsoul_agent.memory.episodic import episodic_memory
            from carsoul_agent.memory.evolution_memory import evolution_memory

            # 注入经验案例
            for i, case_data in enumerate(winter_cases):
                # 经验挖掘
                exp = experience_miner.record_execution(
                    task_type="battery_diagnosis",
                    problem=case_data["problem"],
                    solution=case_data["solution"],
                    result=case_data["result"],
                    success=True,
                    vehicle_id=f"VIN_DEMO_{i+1:03d}",
                    agent_id="powertrain_expert",
                    source_data=case_data["data"],
                    pattern_tags=case_data["tags"],
                )
                results["seeded"].append({"type": "experience", "case_id": exp.case_id})

                # 评估记录
                evaluation_engine.evaluate(
                    agent_id="powertrain_expert",
                    workflow_id=f"demo_task_{i+1}",
                    accuracy=0.75 + i * 0.02,
                    user_satisfaction=0.85,
                    risk_accuracy=0.80,
                    token_consumed=1500 + i * 100,
                    duration_ms=3000 + i * 200,
                )

                # 反思（前几次发现缺少温度因素）
                refl = reflection_engine.reflect(
                    task_id=f"demo_task_{i+1}",
                    agent_id="powertrain_expert",
                    task_type="battery_diagnosis",
                    task_success=True,
                    user_problem_solved=True,
                    missing_data=["environment_temperature"] if i < 2 else [],
                    prediction_accurate=False if i < 2 else True,
                    user_satisfied=True,
                )
                results["seeded"].append({"type": "reflection", "id": refl.reflection_id})

            # 注册初始技能版本
            skill_evolution_engine.register_skill_version(
                skill_id="battery_health_analysis",
                version="v1.0",
                change_log="基于SOH的基础电池健康分析",
                success_rate=0.78,
                accuracy=0.72,
                performance_score=72.0,
            )
            # 更新执行次数以触发进化检测
            skill_evolution_engine.update_skill_performance(
                skill_id="battery_health_analysis",
                version="v1.0",
                execution_count=60,
                success_rate=0.72,
                accuracy=0.68,
                avg_latency_ms=3200,
            )

            # 记录进化里程碑
            evolution_memory.record_milestone(
                agent_id="powertrain_expert",
                milestone_type="experience_discovery",
                description="通过4次冬季电池诊断任务，发现冬季续航下降主要由胎压不足导致",
                before_state={"diagnosis_approach": "仅基于SOH判断"},
                after_state={"discovered_pattern": "Winter Battery Range Loss Pattern"},
                impact_metrics={"cases_analyzed": 4, "confidence": 0.85},
            )

            results["success"] = True
            results["message"] = "演示数据注入完成：4个冬季电池诊断案例 + 反思 + 技能V1.0注册"
        except Exception as exc:  # noqa: BLE001
            results["success"] = False
            results["error"] = str(exc)
            logger.error("Demo data seeding failed: %s", exc)

        return results

    # ------------------------------------------------------------------
    #  Query
    # ------------------------------------------------------------------
    def get_cycle_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """返回进化周期历史."""
        return [c.to_dict() for c in reversed(self._cycles[-limit:])]

    def get_last_cycle(self) -> dict[str, Any] | None:
        """返回最近一次进化周期."""
        if not self._cycles:
            return None
        return self._cycles[-1].to_dict()

    def get_dashboard(self) -> dict[str, Any]:
        """返回进化引擎仪表盘数据 — 前端可视化用."""
        # 聚合各子引擎的状态
        dashboard: dict[str, Any] = {
            "engine_enabled": self._enabled,
            "total_cycles": len(self._cycles),
        }
        # 经验挖掘
        try:
            from carsoul_agent.observation.experience import experience_miner
            dashboard["experience"] = experience_miner.get_summary()
        except Exception:  # noqa: BLE001
            dashboard["experience"] = {"total_cases": 0, "total_patterns": 0}
        # 反思
        try:
            from carsoul_agent.observation.reflection import reflection_engine
            dashboard["reflection"] = reflection_engine.get_summary()
        except Exception:  # noqa: BLE001
            dashboard["reflection"] = {"total_reflections": 0}
        # 技能进化
        try:
            from carsoul_agent.observation.skill_evolution import skill_evolution_engine
            dashboard["skill_evolution"] = skill_evolution_engine.get_summary()
        except Exception:  # noqa: BLE001
            dashboard["skill_evolution"] = {"total_versions": 0}
        # 评估
        try:
            from carsoul_agent.observation.evaluation import evaluation_engine
            dashboard["evaluation"] = evaluation_engine.get_fleet_evaluation()
        except Exception:  # noqa: BLE001
            dashboard["evaluation"] = {"total_evaluations": 0}
        # 优化
        try:
            from carsoul_agent.observation.optimization import optimization_loop
            dashboard["optimization"] = {
                "pending": len(optimization_loop.get_pending_optimizations()),
            }
        except Exception:  # noqa: BLE001
            dashboard["optimization"] = {"pending": 0}
        # 进化记忆
        try:
            from carsoul_agent.memory.evolution_memory import evolution_memory
            dashboard["evolution_memory"] = evolution_memory.get_summary()
        except Exception:  # noqa: BLE001
            dashboard["evolution_memory"] = {"total_milestones": 0}
        # 最近周期
        dashboard["last_cycle"] = self.get_last_cycle()
        return dashboard

    def to_dict(self) -> dict[str, Any]:
        """整体快照."""
        return {
            "total_cycles": len(self._cycles),
            "dashboard": self.get_dashboard(),
            "recent_cycles": [c.to_dict() for c in self._cycles[-5:]],
        }


# Singleton instance.
evolution_engine = EvolutionEngine()
