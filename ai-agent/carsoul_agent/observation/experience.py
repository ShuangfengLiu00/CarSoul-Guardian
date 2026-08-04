"""Experience Mining Engine — 经验挖掘引擎.

Implements Module 01 of the Agent Evolution Engine:
从每天产生的大量任务中挖掘"什么经验值得留下"。

闭环逻辑：
    Agent执行日志 → 车辆状态 → 用户反馈 → 诊断结果 → 维修结果 → 预测结果
                                    ↓
                        Experience Case 提取
                                    ↓
                    模式聚类 → 置信度计算 → 经验库

例如：
    10000次电池诊断 → 发现冬季续航下降 85% 由胎压导致
    → 自动生成 Experience Case (confidence: 92%)
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# 聚类阈值：同一 problem_pattern 出现多少次后形成高置信经验。
_CLUSTER_MIN_COUNT = 3
# 经验置信度阈值：低于此值的经验不进入正式经验库。
_CONFIDENCE_THRESHOLD = 0.60


@dataclass
class ExperienceCase:
    """单条经验案例 — 从一次任务执行中提炼的可复用经验."""

    case_id: str
    task_type: str  # battery_diagnosis / risk_assessment / maintenance / driving_analysis ...
    problem: str  # 问题描述，如"冬季续航下降20%"
    solution: str  # 解决方案，如"调整胎压至2.5bar"
    result: str  # 执行结果，如"续航恢复12%"
    confidence: float = 0.0  # 0–1，经验置信度
    vehicle_id: str = ""
    agent_id: str = ""
    # 经验溯源数据
    source_data: dict[str, Any] = field(default_factory=dict)
    # 关联的模式标签，用于聚类
    pattern_tags: list[str] = field(default_factory=list)
    # 复用统计
    reuse_count: int = 0
    reuse_success_count: int = 0
    created_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def reuse_success_rate(self) -> float:
        """经验复用成功率."""
        return (
            self.reuse_success_count / self.reuse_count
            if self.reuse_count > 0
            else 0.0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "task_type": self.task_type,
            "problem": self.problem,
            "solution": self.solution,
            "result": self.result,
            "confidence": round(self.confidence, 4),
            "vehicle_id": self.vehicle_id,
            "agent_id": self.agent_id,
            "source_data": self.source_data,
            "pattern_tags": self.pattern_tags,
            "reuse_count": self.reuse_count,
            "reuse_success_count": self.reuse_success_count,
            "reuse_success_rate": round(self.reuse_success_rate, 4),
            "created_time": self.created_time,
        }


@dataclass
class ExperiencePattern:
    """经验模式 — 多个相似案例聚类后形成的高阶模式."""

    pattern_id: str
    pattern_name: str  # 如"Winter Battery Range Loss Pattern"
    task_type: str
    description: str  # 模式描述
    common_problem: str  # 共性问题
    common_solution: str  # 共性解决方案
    confidence: float = 0.0  # 聚合置信度
    case_ids: list[str] = field(default_factory=list)
    occurrence_count: int = 0
    success_rate: float = 0.0  # 成功率
    # 关联因素，如 {"temperature": "<5℃", "tire_pressure": "low", "short_trips": "increased"}
    contributing_factors: dict[str, str] = field(default_factory=dict)
    created_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "task_type": self.task_type,
            "description": self.description,
            "common_problem": self.common_problem,
            "common_solution": self.common_solution,
            "confidence": round(self.confidence, 4),
            "case_ids": self.case_ids,
            "occurrence_count": self.occurrence_count,
            "success_rate": round(self.success_rate, 4),
            "contributing_factors": self.contributing_factors,
            "created_time": self.created_time,
        }


class ExperienceMiner:
    """经验挖掘引擎 — 从任务执行中提取可复用经验.

    工作流程：
      1. record_execution: 记录每次任务执行的原始数据
      2. extract_case: 从执行数据中提取经验案例
      3. cluster_patterns: 将相似案例聚类为经验模式
      4. retrieve_similar: 检索相似经验用于新任务
    """

    def __init__(self) -> None:
        self._cases: list[ExperienceCase] = []
        self._patterns: list[ExperiencePattern] = []
        # task_type → list of case indices，加速聚类检索
        self._index_by_task: dict[str, list[int]] = defaultdict(list)

    # ------------------------------------------------------------------
    #  Recording — 记录任务执行
    # ------------------------------------------------------------------
    def record_execution(
        self,
        task_type: str,
        problem: str,
        solution: str,
        result: str,
        success: bool = True,
        vehicle_id: str = "",
        agent_id: str = "",
        source_data: dict[str, Any] | None = None,
        pattern_tags: list[str] | None = None,
    ) -> ExperienceCase:
        """记录一次任务执行并提取经验案例.

        Args:
            task_type: 任务类型（battery_diagnosis / risk_assessment 等）
            problem: 问题描述
            solution: 解决方案
            result: 执行结果
            success: 是否成功
            vehicle_id: 车辆ID
            agent_id: 执行Agent ID
            source_data: 溯源数据（传感器读数、诊断参数等）
            pattern_tags: 模式标签，用于聚类（如["winter", "range_loss", "tire_pressure"]）

        Returns:
            创建的 ExperienceCase
        """
        # 初始置信度基于成功/失败
        confidence = 0.75 if success else 0.40
        case = ExperienceCase(
            case_id=f"exp_{uuid.uuid4().hex[:12]}",
            task_type=task_type,
            problem=problem,
            solution=solution,
            result=result,
            confidence=confidence,
            vehicle_id=vehicle_id,
            agent_id=agent_id,
            source_data=source_data or {},
            pattern_tags=pattern_tags or [],
        )
        idx = len(self._cases)
        self._cases.append(case)
        self._index_by_task[task_type].append(idx)
        logger.info(
            "Experience case recorded: %s (%s) task=%s",
            case.case_id, agent_id, task_type,
        )
        # 如果该任务类型已有足够案例，尝试聚类
        if len(self._index_by_task[task_type]) >= _CLUSTER_MIN_COUNT:
            self._try_cluster(task_type)
        return case

    # ------------------------------------------------------------------
    #  Pattern clustering — 模式聚类
    # ------------------------------------------------------------------
    def _try_cluster(self, task_type: str) -> list[ExperiencePattern]:
        """对同一任务类型的案例进行模式聚类.

        基于 pattern_tags 的重叠度进行分组：tag 重叠 >= 60% 的案例
        归为同一模式。
        """
        indices = self._index_by_task.get(task_type, [])
        if len(indices) < _CLUSTER_MIN_COUNT:
            return []
        # 按 pattern_tags 聚类
        groups: dict[str, list[int]] = defaultdict(list)
        for idx in indices:
            case = self._cases[idx]
            # 用排序后的 tag 组合作为分组键
            key = "|".join(sorted(case.pattern_tags)) if case.pattern_tags else "_no_tags"
            groups[key].append(idx)
        new_patterns: list[ExperiencePattern] = []
        for tag_key, case_indices in groups.items():
            if len(case_indices) < _CLUSTER_MIN_COUNT:
                continue
            # 检查是否已有匹配的 pattern
            existing = self._find_pattern_by_tags(task_type, tag_key)
            if existing is not None:
                # 更新已有 pattern
                self._update_pattern(existing, case_indices)
                continue
            # 创建新 pattern
            cases = [self._cases[i] for i in case_indices]
            pattern = self._build_pattern(task_type, tag_key, cases)
            if pattern.confidence >= _CONFIDENCE_THRESHOLD:
                self._patterns.append(pattern)
                new_patterns.append(pattern)
                logger.info(
                    "New experience pattern discovered: %s (confidence=%.2f, cases=%d)",
                    pattern.pattern_name, pattern.confidence, len(case_indices),
                )
        return new_patterns

    def _build_pattern(
        self,
        task_type: str,
        tag_key: str,
        cases: list[ExperienceCase],
    ) -> ExperiencePattern:
        """从一组案例构建经验模式."""
        # 统计成功案例
        success_cases = [c for c in cases if c.confidence >= 0.5]
        success_rate = len(success_cases) / len(cases) if cases else 0.0
        # 提取共性问题和解决方案（取出现频次最高的）
        common_problem = self._most_common([c.problem for c in cases])
        common_solution = self._most_common([c.solution for c in cases])
        # 聚合置信度
        avg_confidence = sum(c.confidence for c in cases) / len(cases)
        # 提取贡献因素
        factors: dict[str, str] = {}
        for case in cases:
            for k, v in case.source_data.items():
                if k not in factors and isinstance(v, (str, int, float)):
                    factors[k] = str(v)
        # 生成模式名称
        tag_parts = tag_key.split("|") if tag_key != "_no_tags" else [task_type]
        pattern_name = " ".join(w.capitalize() for w in tag_parts[:4])
        if not pattern_name:
            pattern_name = f"{task_type.title()} Pattern"
        return ExperiencePattern(
            pattern_id=f"pat_{uuid.uuid4().hex[:12]}",
            pattern_name=pattern_name,
            task_type=task_type,
            description=f"基于{len(cases)}个案例发现：{common_problem} → {common_solution}",
            common_problem=common_problem,
            common_solution=common_solution,
            confidence=round(avg_confidence, 4),
            case_ids=[c.case_id for c in cases],
            occurrence_count=len(cases),
            success_rate=round(success_rate, 4),
            contributing_factors=factors,
        )

    def _update_pattern(
        self,
        pattern: ExperiencePattern,
        new_case_indices: list[int],
    ) -> None:
        """用新案例更新已有模式."""
        new_cases = [self._cases[i] for i in new_case_indices]
        all_case_ids = set(pattern.case_ids)
        for c in new_cases:
            all_case_ids.add(c.case_id)
        pattern.case_ids = list(all_case_ids)
        pattern.occurrence_count = len(pattern.case_ids)
        # 重新计算置信度
        all_cases = [c for c in self._cases if c.case_id in all_case_ids]
        if all_cases:
            pattern.confidence = round(
                sum(c.confidence for c in all_cases) / len(all_cases), 4
            )
            pattern.success_rate = round(
                len([c for c in all_cases if c.confidence >= 0.5]) / len(all_cases), 4
            )

    def _find_pattern_by_tags(
        self,
        task_type: str,
        tag_key: str,
    ) -> ExperiencePattern | None:
        """查找已有匹配标签的模式."""
        for p in self._patterns:
            if p.task_type != task_type:
                continue
            existing_key = "|".join(sorted(
                p.description.lower().split()
            ))
            if existing_key == tag_key:
                return p
        return None

    @staticmethod
    def _most_common(items: list[str]) -> str:
        """返回列表中出现频次最高的元素."""
        if not items:
            return ""
        counts: dict[str, int] = defaultdict(int)
        for item in items:
            counts[item] += 1
        return max(counts, key=counts.get)

    # ------------------------------------------------------------------
    #  Retrieval — 经验检索
    # ------------------------------------------------------------------
    def retrieve_similar(
        self,
        task_type: str,
        problem: str = "",
        pattern_tags: list[str] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """检索相似经验案例和模式，供新任务复用.

        匹配优先级：
          1. task_type + pattern_tags 重叠 → 高匹配
          2. task_type + problem 关键词匹配 → 中匹配
          3. task_type 相同 → 低匹配
        """
        results: list[tuple[float, dict[str, Any]]] = []
        # 先匹配模式
        for pattern in self._patterns:
            if pattern.task_type != task_type:
                continue
            score = pattern.confidence
            if pattern_tags:
                tag_overlap = len(
                    set(pattern_tags) & set(pattern.contributing_factors.keys())
                )
                score += tag_overlap * 0.1
            if problem and problem.lower() in pattern.common_problem.lower():
                score += 0.15
            results.append((score, {"type": "pattern", **pattern.to_dict()}))
        # 再匹配案例
        for case in self._cases:
            if case.task_type != task_type:
                continue
            score = case.confidence
            if pattern_tags:
                tag_overlap = len(set(pattern_tags) & set(case.pattern_tags))
                score += tag_overlap * 0.1
            if problem and problem.lower() in case.problem.lower():
                score += 0.15
            results.append((score, {"type": "case", **case.to_dict()}))
        # 按分数排序
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    def record_reuse(
        self,
        case_id: str,
        success: bool,
    ) -> bool:
        """记录经验案例的复用结果."""
        for case in self._cases:
            if case.case_id == case_id:
                case.reuse_count += 1
                if success:
                    case.reuse_success_count += 1
                # 根据复用结果调整置信度
                if success:
                    case.confidence = min(1.0, case.confidence + 0.02)
                else:
                    case.confidence = max(0.0, case.confidence - 0.05)
                return True
        return False

    # ------------------------------------------------------------------
    #  Query
    # ------------------------------------------------------------------
    def get_all_cases(self, limit: int = 100) -> list[dict[str, Any]]:
        """返回所有经验案例（newest first）."""
        return [c.to_dict() for c in reversed(self._cases[-limit:])]

    def get_all_patterns(self) -> list[dict[str, Any]]:
        """返回所有经验模式."""
        return [p.to_dict() for p in self._patterns]

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        """返回指定案例."""
        for case in self._cases:
            if case.case_id == case_id:
                return case.to_dict()
        return None

    def get_summary(self) -> dict[str, Any]:
        """经验挖掘摘要."""
        per_task: dict[str, int] = defaultdict(int)
        for case in self._cases:
            per_task[case.task_type] += 1
        avg_confidence = (
            sum(c.confidence for c in self._cases) / len(self._cases)
            if self._cases
            else 0.0
        )
        return {
            "total_cases": len(self._cases),
            "total_patterns": len(self._patterns),
            "avg_confidence": round(avg_confidence, 4),
            "cases_per_task_type": dict(per_task),
            "top_patterns": [p.to_dict() for p in self._patterns[:5]],
            "recent_cases": [c.to_dict() for c in self._cases[-10:]],
        }

    def to_dict(self) -> dict[str, Any]:
        """整体快照."""
        return {
            "summary": self.get_summary(),
            "patterns": self.get_all_patterns(),
        }


# Singleton instance.
experience_miner = ExperienceMiner()
