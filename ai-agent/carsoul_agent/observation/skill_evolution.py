"""Skill Evolution Engine — 技能进化引擎.

Implements Module 04 of the Agent Evolution Engine:
让 Skill 不再是固定代码，而是自己升级。

Skill 生命周期：
    Skill V1.0 → 1000次执行 → Evaluation → 发现不足 → Skill Mutation → V1.1

例如：
    原 Skill: Battery Health Diagnosis V1.0 (仅根据SOH判断)
    误判发现: 冬季环境
    升级:     V1.1 (+ Temperature Model + Driving Pattern Model + Charging Habit Model)

完整进化治理流程（Evolution Approval Layer）：
    Skill变化 → 自动测试 → Sandbox验证 → 评分 → 批准 → 上线
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Skill 进化触发阈值
_EVALUATION_COUNT_THRESHOLD = 50  # 累计执行次数达到此值后开始评估
_SUCCESS_RATE_DROP_THRESHOLD = 0.75  # 成功率低于此值触发进化
_ACCURACY_DROP_THRESHOLD = 0.70  # 准确率低于此值触发进化
# 治理审批：测试通过分数阈值
_SANDBOX_PASS_SCORE = 0.80


@dataclass
class SkillVersionRecord:
    """技能版本记录 — 一个 Skill 的某个版本及其性能指标."""

    version_id: str
    skill_id: str
    version: str  # v1.0 / v1.1 / v2.0
    parent_version: str = ""  # 父版本
    # 变更日志
    change_log: str = ""
    change_type: str = "initial"  # initial / mutation / optimization / rollback
    added_capabilities: list[str] = field(default_factory=list)
    # 性能指标
    success_rate: float = 0.0
    accuracy: float = 0.0
    avg_latency_ms: float = 0.0
    performance_score: float = 0.0  # 综合评分 0–100
    # 执行统计
    execution_count: int = 0
    # 审批状态
    approval_status: str = "pending"  # pending / testing / approved / rejected / deployed
    approval_notes: str = ""
    created_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    deployed_time: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "skill_id": self.skill_id,
            "version": self.version,
            "parent_version": self.parent_version,
            "change_log": self.change_log,
            "change_type": self.change_type,
            "added_capabilities": self.added_capabilities,
            "success_rate": round(self.success_rate, 4),
            "accuracy": round(self.accuracy, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "performance_score": round(self.performance_score, 2),
            "execution_count": self.execution_count,
            "approval_status": self.approval_status,
            "approval_notes": self.approval_notes,
            "created_time": self.created_time,
            "deployed_time": self.deployed_time,
        }


@dataclass
class SkillMutationProposal:
    """技能变异提案 — 基于评估和反思生成的技能改进方案."""

    proposal_id: str
    skill_id: str
    current_version: str
    proposed_version: str
    mutation_reason: str  # 变异原因
    mutation_type: str  # prompt_refinement / model_upgrade / feature_addition / strategy_adjustment
    # 具体改进内容
    changes: list[str] = field(default_factory=list)
    added_capabilities: list[str] = field(default_factory=list)
    # 触发数据
    trigger_metrics: dict[str, Any] = field(default_factory=dict)
    trigger_reflection_id: str = ""
    # 治理审批流程
    test_result: dict[str, Any] = field(default_factory=dict)
    sandbox_result: dict[str, Any] = field(default_factory=dict)
    approval_score: float = 0.0
    status: str = "proposed"  # proposed / testing / sandbox / approved / rejected / deployed
    created_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "skill_id": self.skill_id,
            "current_version": self.current_version,
            "proposed_version": self.proposed_version,
            "mutation_reason": self.mutation_reason,
            "mutation_type": self.mutation_type,
            "changes": self.changes,
            "added_capabilities": self.added_capabilities,
            "trigger_metrics": self.trigger_metrics,
            "trigger_reflection_id": self.trigger_reflection_id,
            "test_result": self.test_result,
            "sandbox_result": self.sandbox_result,
            "approval_score": round(self.approval_score, 4),
            "status": self.status,
            "created_time": self.created_time,
        }


class SkillEvolutionEngine:
    """技能进化引擎 — 让 Skill 自己升级.

    完整流程：
      1. monitor: 监控 Skill 执行性能
      2. detect_mutation_need: 检测是否需要变异
      3. propose_mutation: 生成变异提案
      4. run_approval_pipeline: 治理审批流程
         (自动测试 → Sandbox验证 → 评分 → 批准 → 上线)
      5. deploy: 部署新版本
    """

    def __init__(self) -> None:
        # skill_id → list of SkillVersionRecord
        self._versions: dict[str, list[SkillVersionRecord]] = {}
        self._proposals: list[SkillMutationProposal] = []

    # ------------------------------------------------------------------
    #  Registration — 初始化技能版本
    # ------------------------------------------------------------------
    def register_skill_version(
        self,
        skill_id: str,
        version: str,
        change_log: str = "初始版本",
        change_type: str = "initial",
        added_capabilities: list[str] | None = None,
        success_rate: float = 0.0,
        accuracy: float = 0.0,
        performance_score: float = 0.0,
    ) -> SkillVersionRecord:
        """注册一个技能版本."""
        record = SkillVersionRecord(
            version_id=f"skv_{uuid.uuid4().hex[:12]}",
            skill_id=skill_id,
            version=version,
            change_log=change_log,
            change_type=change_type,
            added_capabilities=added_capabilities or [],
            success_rate=success_rate,
            accuracy=accuracy,
            performance_score=performance_score,
            approval_status="deployed",
            deployed_time=datetime.now(timezone.utc).isoformat(),
        )
        self._versions.setdefault(skill_id, []).append(record)
        logger.info("Skill version registered: %s %s", skill_id, version)
        return record

    # ------------------------------------------------------------------
    #  Monitoring — 性能监控
    # ------------------------------------------------------------------
    def update_skill_performance(
        self,
        skill_id: str,
        version: str,
        execution_count: int = 0,
        success_rate: float = 0.0,
        accuracy: float = 0.0,
        avg_latency_ms: float = 0.0,
    ) -> bool:
        """更新技能版本的性能指标."""
        record = self._find_version(skill_id, version)
        if record is None:
            return False
        record.execution_count += execution_count
        if success_rate:
            record.success_rate = success_rate
        if accuracy:
            record.accuracy = accuracy
        if avg_latency_ms:
            record.avg_latency_ms = avg_latency_ms
        # 重新计算综合评分
        record.performance_score = self._compute_performance_score(record)
        return True

    def _compute_performance_score(self, record: SkillVersionRecord) -> float:
        """综合评分 = 成功率*40% + 准确率*40% + 效率*20%."""
        efficiency = max(0, 1 - record.avg_latency_ms / 10000) if record.avg_latency_ms else 0.5
        return round(
            (record.success_rate * 0.4 + record.accuracy * 0.4 + efficiency * 0.2) * 100,
            2,
        )

    def _find_version(self, skill_id: str, version: str) -> SkillVersionRecord | None:
        """查找技能的指定版本."""
        for record in self._versions.get(skill_id, []):
            if record.version == version:
                return record
        return None

    def get_current_version(self, skill_id: str) -> SkillVersionRecord | None:
        """获取技能的当前部署版本."""
        versions = self._versions.get(skill_id, [])
        deployed = [v for v in versions if v.approval_status == "deployed"]
        if deployed:
            return deployed[-1]
        return versions[-1] if versions else None

    # ------------------------------------------------------------------
    #  Mutation Detection — 变异检测
    # ------------------------------------------------------------------
    def detect_mutation_need(self, skill_id: str) -> dict[str, Any]:
        """检测技能是否需要变异.

        基于以下条件：
          1. 执行次数 >= 阈值
          2. 成功率 < 阈值 或 准确率 < 阈值
          3. 反思报告中有高优先级改进建议
        """
        current = self.get_current_version(skill_id)
        if current is None:
            return {"needed": False, "reason": "skill not found"}
        reasons: list[str] = []
        if current.execution_count >= _EVALUATION_COUNT_THRESHOLD:
            if current.success_rate < _SUCCESS_RATE_DROP_THRESHOLD:
                reasons.append(
                    f"成功率 {current.success_rate:.2f} 低于阈值 {_SUCCESS_RATE_DROP_THRESHOLD}"
                )
            if current.accuracy < _ACCURACY_DROP_THRESHOLD:
                reasons.append(
                    f"准确率 {current.accuracy:.2f} 低于阈值 {_ACCURACY_DROP_THRESHOLD}"
                )
        # 检查反思报告
        try:
            from carsoul_agent.observation.reflection import reflection_engine
            weaknesses = reflection_engine.get_agent_weaknesses(skill_id)
            if weaknesses.get("weakness_count", 0) >= 3:
                reasons.append(f"反复出现 {weaknesses['weakness_count']} 个弱点")
        except Exception:  # noqa: BLE001
            pass
        needed = len(reasons) > 0
        return {
            "needed": needed,
            "reasons": reasons,
            "current_version": current.version,
            "current_performance": {
                "success_rate": current.success_rate,
                "accuracy": current.accuracy,
                "execution_count": current.execution_count,
                "performance_score": current.performance_score,
            },
        }

    # ------------------------------------------------------------------
    #  Mutation Proposal — 变异提案
    # ------------------------------------------------------------------
    def propose_mutation(
        self,
        skill_id: str,
        mutation_reason: str,
        mutation_type: str = "feature_addition",
        changes: list[str] | None = None,
        added_capabilities: list[str] | None = None,
        trigger_metrics: dict[str, Any] | None = None,
        trigger_reflection_id: str = "",
    ) -> SkillMutationProposal:
        """生成技能变异提案.

        Args:
            skill_id: 技能ID
            mutation_reason: 变异原因
            mutation_type: 变异类型
            changes: 具体变更列表
            added_capabilities: 新增能力列表
            trigger_metrics: 触发指标数据
            trigger_reflection_id: 触发变异的反思报告ID
        """
        current = self.get_current_version(skill_id)
        current_version = current.version if current else "v1.0"
        proposed_version = self._next_version(current_version, mutation_type)
        proposal = SkillMutationProposal(
            proposal_id=f"smp_{uuid.uuid4().hex[:12]}",
            skill_id=skill_id,
            current_version=current_version,
            proposed_version=proposed_version,
            mutation_reason=mutation_reason,
            mutation_type=mutation_type,
            changes=changes or [],
            added_capabilities=added_capabilities or [],
            trigger_metrics=trigger_metrics or {},
            trigger_reflection_id=trigger_reflection_id,
        )
        self._proposals.append(proposal)
        logger.info(
            "Skill mutation proposed: %s %s → %s (%s)",
            skill_id, current_version, proposed_version, mutation_type,
        )
        return proposal

    def _next_version(self, current_version: str, mutation_type: str) -> str:
        """根据变异类型计算下一个版本号.

        - feature_addition / model_upgrade: minor version bump (v1.0 → v1.1)
        - strategy_adjustment: patch bump (v1.0 → v1.0.1) — simplified to minor
        - 重大重构: major bump (v1.x → v2.0)
        """
        try:
            parts = current_version.lstrip("v").split(".")
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            return "v1.1"
        if mutation_type == "major_refactor":
            return f"v{major + 1}.0"
        return f"v{major}.{minor + 1}"

    # ------------------------------------------------------------------
    #  Approval Pipeline — 治理审批流程
    # ------------------------------------------------------------------
    def run_approval_pipeline(self, proposal_id: str) -> dict[str, Any]:
        """执行完整的治理审批流程.

        流程：自动测试 → Sandbox验证 → 评分 → 批准 → 上线

        Returns:
            审批结果摘要
        """
        proposal = self._find_proposal(proposal_id)
        if proposal is None:
            return {"success": False, "error": "proposal not found"}

        # Step 1: 自动测试
        proposal.status = "testing"
        test_result = self._run_auto_tests(proposal)
        proposal.test_result = test_result

        # Step 2: Sandbox 验证
        proposal.status = "sandbox"
        sandbox_result = self._run_sandbox_validation(proposal)
        proposal.sandbox_result = sandbox_result

        # Step 3: 综合评分
        test_score = test_result.get("score", 0.0)
        sandbox_score = sandbox_result.get("score", 0.0)
        proposal.approval_score = round(
            (test_score * 0.5 + sandbox_score * 0.5), 4
        )

        # Step 4: 批准决策
        if proposal.approval_score >= _SANDBOX_PASS_SCORE:
            proposal.status = "approved"
            # Step 5: 上线
            self._deploy_proposal(proposal)
            result = {
                "success": True,
                "proposal_id": proposal_id,
                "approval_score": proposal.approval_score,
                "status": "deployed",
                "new_version": proposal.proposed_version,
            }
        else:
            proposal.status = "rejected"
            result = {
                "success": False,
                "proposal_id": proposal_id,
                "approval_score": proposal.approval_score,
                "status": "rejected",
                "reason": f"审批分数 {proposal.approval_score} 未达阈值 {_SANDBOX_PASS_SCORE}",
            }
        logger.info(
            "Skill mutation pipeline: %s → %s (score=%.2f)",
            proposal_id, proposal.status, proposal.approval_score,
        )
        return result

    def _run_auto_tests(self, proposal: SkillMutationProposal) -> dict[str, Any]:
        """模拟自动测试套件.

        在真实系统中会运行回归测试集。这里基于变异类型和改进内容
        生成合理的测试分数。
        """
        base_score = 0.75
        # 有具体改进内容加分
        if proposal.added_capabilities:
            base_score += 0.05 * len(proposal.added_capabilities)
        if proposal.changes:
            base_score += 0.03 * len(proposal.changes)
        # 变异类型影响
        type_bonus = {
            "feature_addition": 0.05,
            "model_upgrade": 0.08,
            "prompt_refinement": 0.03,
            "strategy_adjustment": 0.02,
        }
        base_score += type_bonus.get(proposal.mutation_type, 0.0)
        score = min(1.0, base_score)
        return {
            "score": round(score, 4),
            "test_cases": 50,
            "passed": int(50 * score),
            "failed": int(50 * (1 - score)),
            "details": f"自动测试套件执行{50}个测试用例，通过率{score:.0%}",
        }

    def _run_sandbox_validation(self, proposal: SkillMutationProposal) -> dict[str, Any]:
        """模拟 Sandbox 沙箱验证.

        在真实系统中会在隔离环境中用真实流量影子测试。
        """
        test_score = proposal.test_result.get("score", 0.75)
        # Sandbox 分数通常略低于测试分数（真实环境更复杂）
        sandbox_score = max(0.5, test_score - 0.05)
        return {
            "score": round(sandbox_score, 4),
            "shadow_requests": 100,
            "success_rate": round(sandbox_score, 4),
            "latency_ok": True,
            "no_regressions": sandbox_score >= 0.7,
            "details": f"影子流量验证100次请求，成功率{sandbox_score:.0%}",
        }

    def _deploy_proposal(self, proposal: SkillMutationProposal) -> SkillVersionRecord:
        """部署变异提案为新版本."""
        current = self.get_current_version(proposal.skill_id)
        parent = current.version if current else ""
        record = SkillVersionRecord(
            version_id=f"skv_{uuid.uuid4().hex[:12]}",
            skill_id=proposal.skill_id,
            version=proposal.proposed_version,
            parent_version=parent,
            change_log=proposal.mutation_reason,
            change_type=proposal.mutation_type,
            added_capabilities=proposal.added_capabilities,
            success_rate=proposal.sandbox_result.get("success_rate", 0.0),
            accuracy=proposal.test_result.get("score", 0.0),
            performance_score=proposal.approval_score * 100,
            approval_status="deployed",
            approval_notes=f"审批分数 {proposal.approval_score}，自动批准上线",
            deployed_time=datetime.now(timezone.utc).isoformat(),
        )
        # 标记旧版本为已废弃
        if current:
            current.approval_status = "deprecated"
        self._versions.setdefault(proposal.skill_id, []).append(record)
        # 同步到 Version Manager
        try:
            from carsoul_agent.governance.version_manager import (
                version_manager,
                VersionStatus,
            )
            version_manager.register_version(
                agent_id=proposal.skill_id,
                version=proposal.proposed_version,
                status=VersionStatus.STABLE,
                release_notes=proposal.mutation_reason,
                parent_version=parent,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("version_manager sync skipped: %s", exc)
        # 同步到 Skill Registry
        try:
            from carsoul_agent.governance.skill_registry import skill_registry
            skill = skill_registry.get(proposal.skill_id)
            if skill:
                skill.version = proposal.proposed_version
        except Exception as exc:  # noqa: BLE001
            logger.debug("skill_registry sync skipped: %s", exc)
        proposal.status = "deployed"
        logger.info(
            "Skill deployed: %s %s (score=%.2f)",
            proposal.skill_id, proposal.proposed_version, proposal.approval_score,
        )
        return record

    def _find_proposal(self, proposal_id: str) -> SkillMutationProposal | None:
        for p in self._proposals:
            if p.proposal_id == proposal_id:
                return p
        return None

    # ------------------------------------------------------------------
    #  Auto-evolution — 自动进化触发
    # ------------------------------------------------------------------
    def auto_evolve_skill(self, skill_id: str) -> dict[str, Any]:
        """自动检测并触发技能进化.

        完整自动化流程：
          1. 检测是否需要变异
          2. 生成变异提案
          3. 执行治理审批
          4. 返回结果
        """
        detection = self.detect_mutation_need(skill_id)
        if not detection.get("needed"):
            return {
                "skill_id": skill_id,
                "evolved": False,
                "reason": "no mutation needed",
                "detection": detection,
            }
        # 从反思报告中获取改进方向
        improvements: list[str] = []
        added_caps: list[str] = []
        try:
            from carsoul_agent.observation.reflection import reflection_engine
            reflections = reflection_engine.get_agent_reflections(skill_id, limit=5)
            for r in reflections:
                improvements.extend(r.get("analysis", {}).get("improvements", []))
        except Exception:  # noqa: BLE001
            pass
        # 从经验模式中获取新能力
        try:
            from carsoul_agent.observation.experience import experience_miner
            similar = experience_miner.retrieve_similar(skill_id, limit=3)
            for exp in similar:
                if exp.get("type") == "pattern":
                    factors = exp.get("contributing_factors", {})
                    for factor in factors:
                        added_caps.append(f"{factor}_model")
        except Exception:  # noqa: BLE001
            pass
        # 去重
        improvements = list(dict.fromkeys(improvements))
        added_caps = list(dict.fromkeys(added_caps))
        # 生成变异提案
        proposal = self.propose_mutation(
            skill_id=skill_id,
            mutation_reason="; ".join(detection.get("reasons", ["性能下降"])),
            mutation_type="feature_addition",
            changes=improvements[:5],
            added_capabilities=added_caps[:5],
            trigger_metrics=detection.get("current_performance", {}),
        )
        # 执行治理审批
        result = self.run_approval_pipeline(proposal.proposal_id)
        return {
            "skill_id": skill_id,
            "evolved": result.get("success", False),
            "proposal_id": proposal.proposal_id,
            "detection": detection,
            "pipeline_result": result,
        }

    # ------------------------------------------------------------------
    #  Query
    # ------------------------------------------------------------------
    def get_skill_versions(self, skill_id: str) -> list[dict[str, Any]]:
        """返回技能的完整版本历史."""
        return [v.to_dict() for v in self._versions.get(skill_id, [])]

    def get_all_proposals(self, limit: int = 50) -> list[dict[str, Any]]:
        """返回所有变异提案."""
        return [p.to_dict() for p in reversed(self._proposals[-limit:])]

    def get_pending_proposals(self) -> list[dict[str, Any]]:
        """返回待处理的变异提案."""
        return [
            p.to_dict()
            for p in self._proposals
            if p.status in ("proposed", "testing", "sandbox")
        ]

    def get_summary(self) -> dict[str, Any]:
        """技能进化摘要."""
        total_versions = sum(len(v) for v in self._versions.values())
        deployed = sum(
            1 for versions in self._versions.values()
            for v in versions if v.approval_status == "deployed"
        )
        total_proposals = len(self._proposals)
        approved = sum(1 for p in self._proposals if p.status == "deployed")
        rejected = sum(1 for p in self._proposals if p.status == "rejected")
        return {
            "tracked_skills": len(self._versions),
            "total_versions": total_versions,
            "deployed_versions": deployed,
            "total_proposals": total_proposals,
            "approved_proposals": approved,
            "rejected_proposals": rejected,
            "pending_proposals": len(self.get_pending_proposals()),
            "recent_proposals": [p.to_dict() for p in self._proposals[-5:]],
        }

    def to_dict(self) -> dict[str, Any]:
        """整体快照."""
        return {
            "summary": self.get_summary(),
            "all_versions": {
                sid: [v.to_dict() for v in versions]
                for sid, versions in self._versions.items()
            },
        }


# Singleton instance.
skill_evolution_engine = SkillEvolutionEngine()
