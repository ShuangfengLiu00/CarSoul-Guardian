"""CarSoul Agent Observation Layer — 智能体观测层 + 进化引擎.

对应《CarSoul Guardian Agent Infra Architecture》第四层 Agent Observation Layer:
  - Trace: 全链路追踪（含Token消耗）
  - Evaluation: Agent评估（准确率/响应效率/用户满意度/风险率）
  - Optimization: 自动优化闭环（Collect → Analyze → Evaluate → Optimize）
  - Evolution: Agent自进化机制

对应《CarSoul Guardian Agent Evolution Engine V1.0》新增模块:
  - Experience: 经验挖掘引擎（从任务中提取可复用经验）
  - Reflection: 反思引擎（任务后自动复盘）
  - SkillEvolution: 技能进化引擎（Skill版本生命周期管理）
  - EvolutionEngine: 进化闭环编排器（串联所有子引擎）
"""
from carsoul_agent.observation.trace import TraceCollector, trace_collector
from carsoul_agent.observation.evaluation import EvaluationEngine, evaluation_engine
from carsoul_agent.observation.optimization import OptimizationLoop, optimization_loop
from carsoul_agent.observation.evolution import EvolutionManager, evolution_manager
from carsoul_agent.observation.experience import (
    ExperienceMiner,
    ExperienceCase,
    ExperiencePattern,
    experience_miner,
)
from carsoul_agent.observation.reflection import (
    ReflectionEngine,
    ReflectionReport,
    reflection_engine,
)
from carsoul_agent.observation.skill_evolution import (
    SkillEvolutionEngine,
    SkillVersionRecord,
    SkillMutationProposal,
    skill_evolution_engine,
)
from carsoul_agent.observation.evolution_engine import (
    EvolutionEngine,
    EvolutionCycleResult,
    evolution_engine,
)

__all__ = [
    # Original observation modules
    "TraceCollector", "trace_collector",
    "EvaluationEngine", "evaluation_engine",
    "OptimizationLoop", "optimization_loop",
    "EvolutionManager", "evolution_manager",
    # Evolution Engine modules
    "ExperienceMiner", "ExperienceCase", "ExperiencePattern", "experience_miner",
    "ReflectionEngine", "ReflectionReport", "reflection_engine",
    "SkillEvolutionEngine", "SkillVersionRecord", "SkillMutationProposal",
    "skill_evolution_engine",
    "EvolutionEngine", "EvolutionCycleResult", "evolution_engine",
]
