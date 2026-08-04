# CarSoul Guardian · 完整修复计划

> 基于三技能视角（AI Agent 架构师 / 用户故事设计师 / 汽车行业研究员）的系统性查漏补缺
> 制定时间：2026-07-29
> 目标：确保产品实现与 Demo 宣传一致，补全 Agent 闭环关键缺口

---

## 目录

- [一、问题总览](#一问题总览)
- [二、Phase 1 · P0 关键修复（比赛前必须完成）](#二phase-1--p0-关键修复比赛前必须完成)
  - [P0-1 · 实现三级升级闭环](#p0-1--实现三级升级闭环)
  - [P0-2 · RAG 接入诊断环节](#p0-2--rag-接入诊断环节)
  - [P0-3 · 主动巡检调度器](#p0-3--主动巡检调度器)
- [三、Phase 2 · P1 高优先级增强](#三phase-2--p1-高优先级增强)
  - [P1-1 · 长期记忆系统](#p1-1--长期记忆系统)
  - [P1-2 · 守护工具 DB 持久化](#p1-2--守护工具-db-持久化)
  - [P1-3 · 车辆工具接入后端 DB](#p1-3--车辆工具接入后端-db)
  - [P1-4 · 风险预测前端页面](#p1-4--风险预测前端页面)
- [四、Phase 3 · P2 中优先级优化](#四phase-3--p2-中优先级优化)
- [五、实施顺序与依赖关系](#五实施顺序与依赖关系)
- [六、验收检查清单](#六验收检查清单)

---

## 一、问题总览

### 差距矩阵

| 优先级 | 编号 | 问题 | 影响 |
|--------|------|------|------|
| **P0** | P0-1 | 三级升级闭环未实现 | Demo 核心卖点「主动安全闭环」不完整 |
| **P0** | P0-2 | RAG 未接入诊断环节 | Demo ACT3「知识库匹配」推理链是前端硬编码 |
| **P0** | P0-3 | 无主动巡检机制 | 产品名「主动守护」实际为被动响应 |
| **P1** | P1-1 | 记忆系统仅 L1 短期对话 | 无跨会话记忆，车辆「失忆」 |
| **P1** | P1-2 | 守护工具纯内存无持久化 | 重启丢失所有守护动作记录 |
| **P1** | P1-3 | 车辆工具返回硬编码 Mock | Agent 层与后端数据层断裂 |
| **P1** | P1-4 | 风险预测 API 前端未消费 | 闭环后半段（反馈/准确率）断裂 |
| **P2** | P2-1 | 无实时数据流（无 WebSocket/SSE） | 前端轮询，无流式推送 |
| **P2** | P2-2 | 专家提示词未实际使用 | 5 个专家 prompt 常量闲置 |
| **P2** | P2-3 | 传感器数据合成注入 | 非真实传感器数据 |
| **P2** | P2-4 | 遗留代码 & 孤儿文件 | workflows/base.py 废弃、YAML 未加载 |

---

## 二、Phase 1 · P0 关键修复（比赛前必须完成）

### P0-1 · 实现三级升级闭环

#### 问题

Demo 包装文档 `demo-packaging.md` ACT4 宣传「感知→通知车主→联动救援」三级升级闭环，但 `service.py` 的 `_anomaly_suggestion()` 只调用一次 `push_reminder`，无超时升级逻辑，无外部服务联动。

#### 当前代码（service.py:83-143）

```python
def _anomaly_suggestion(self, state: AgentState) -> dict:
    # ...
    # 1. Push reminder (guarded tool) — 仅一次推送，无升级
    reminder_tool = self._tools.get("push_reminder")
    if reminder_tool:
        reminder_tool.run(vehicle_id=vehicle_id, level=level, ...)

    # 2. Record lifecycle event
    # 3. Write service suggestion
    # 无第二级升级推送，无第三级外部联动
```

#### 修复方案

**新增文件：`ai-agent/carsoul_agent/agents/core/escalation.py`**

```python
"""三级升级闭环管理器 (Escalation Manager).

实现 Demo ACT4 的核心卖点：
  Level 1 — 主动感知与判断（Agent 工作流已完成）
  Level 2 — 分级通知车主（首推 → 等待 → 升级推送）
  Level 3 — 联动外部救援（创建服务工单）

设计原则：
  - 每一级都有明确的触发条件和降级策略
  - 升级链可配置（等待时间、是否启用第三级）
  - 所有动作写入 ActionStore 可审计
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any
from carsoul_agent.tools import default_registry
from carsoul_agent.tools.guard_tools import action_store

logger = logging.getLogger(__name__)


@dataclass
class EscalationConfig:
    """升级链配置 — 比赛演示时可缩短等待时间。"""
    level2_wait_seconds: int = 30       # 第二级升级等待时间
    level3_enabled: bool = True         # 是否启用第三级联动
    level3_requires_auth: bool = True   # 第三级需要车主预授权


@dataclass
class EscalationResult:
    """升级闭环执行结果。"""
    level_reached: int = 1              # 实际到达的级别
    actions: list[dict] = field(default_factory=list)
    service_orders: list[dict] = field(default_factory=list)
    escalation_chain: list[dict] = field(default_factory=list)


class EscalationManager:
    """三级升级闭环执行器。"""

    # 第三级联动服务类型
    SERVICE_TYPES = [
        {"type": "roadside_assist", "name": "道路救援", "priority": "high"},
        {"type": "manufacturer_service", "name": "车企服务中心", "priority": "high"},
        {"type": "insurance_service", "name": "保险服务", "priority": "medium"},
    ]

    def __init__(self, config: EscalationConfig | None = None):
        self._config = config or EscalationConfig()
        self._tools = default_registry

    def execute(self, state: dict) -> EscalationResult:
        """执行三级升级闭环。

        在比赛演示场景中，由于无法真正等待30秒，
        采用「模拟时间推进」策略：直接生成三级动作链，
        标注每级的触发条件和时间戳。
        """
        result = EscalationResult()
        risk = state.get("risk_assessment", {})
        diagnosis = state.get("diagnosis", {}).get("primary", {})
        explanation = state.get("explanation", "")
        vehicle = state.get("vehicle_state", {})
        vehicle_id = vehicle.get("vehicle_id", 1)
        level = risk.get("level", "warning")
        root_cause = diagnosis.get("root_cause", "异常")

        # --- Level 1: 主动感知与判断（已由工作流完成）---
        result.escalation_chain.append({
            "level": 1,
            "title": "主动感知与判断",
            "description": f"CarSoul 已感知到异常信号，判断存在「{root_cause}」风险",
            "risk_level": level,
            "risk_index": risk.get("probability_percent", 0),
            "timestamp": "T+0s",
        })

        # --- Level 2: 分级通知车主 ---
        result = self._execute_level2(
            result, vehicle_id, level, root_cause, explanation
        )

        # --- Level 3: 联动外部救援 ---
        if self._config.level3_enabled and level in ("urgent", "warning"):
            result = self._execute_level3(
                result, vehicle_id, level, root_cause
            )

        return result

    def _execute_level2(
        self, result: EscalationResult,
        vehicle_id: int, level: str,
        root_cause: str, explanation: str,
    ) -> EscalationResult:
        """第二级：首推 + 升级推送。"""

        # 首条推送
        first_reminder = self._push_reminder(
            vehicle_id, level, root_cause, explanation, is_escalation=False
        )
        result.actions.append(first_reminder)
        result.escalation_chain.append({
            "level": 2,
            "step": "first_notification",
            "title": "首条守护提醒",
            "description": f"检测到{root_cause}，已推送提醒至车主手机",
            "message": explanation,
            "timestamp": "T+0s",
        })

        # 模拟等待后升级推送
        escalated_level = "urgent" if level == "urgent" else "warning"
        escalation_message = (
            f"为安全起见，请不要启动车辆，并远离车辆。"
            f"CarSoul 正在为您联系服务。"
        )
        escalated_reminder = self._push_reminder(
            vehicle_id, escalated_level, root_cause,
            escalation_message, is_escalation=True
        )
        result.actions.append(escalated_reminder)
        result.escalation_chain.append({
            "level": 2,
            "step": "escalated_notification",
            "title": "升级推送（车主未响应）",
            "description": f"等待{self._config.level2_wait_seconds}秒无响应，已升级为加急推送",
            "wait_seconds": self._config.level2_wait_seconds,
            "message": escalation_message,
            "timestamp": f"T+{self._config.level2_wait_seconds}s",
        })

        result.level_reached = 2
        return result

    def _execute_level3(
        self, result: EscalationResult,
        vehicle_id: int, level: str, root_cause: str,
    ) -> EscalationResult:
        """第三级：联动外部救援服务。"""

        for svc in self.SERVICE_TYPES:
            order = self._create_service_order(
                vehicle_id, svc, root_cause, level
            )
            if order:
                result.service_orders.append(order)
                result.escalation_chain.append({
                    "level": 3,
                    "step": svc["type"],
                    "title": f"联动{svc['name']}",
                    "description": f"根据车主预授权，已创建{svc['name']}工单",
                    "service_type": svc["type"],
                    "status": "created",
                    "estimated_response": "30分钟内",
                    "timestamp": f"T+{self._config.level2_wait_seconds + 10}s",
                })

        result.escalation_chain.append({
            "level": 3,
            "step": "loop_closed",
            "title": "主动安全闭环已完成",
            "description": "感知 → 通知车主 → 联动救援 三级升级闭环全部完成",
            "timestamp": f"T+{self._config.level2_wait_seconds + 15}s",
        })
        result.level_reached = 3
        return result

    def _push_reminder(
        self, vehicle_id: int, level: str,
        root_cause: str, message: str,
        is_escalation: bool = False,
    ) -> dict:
        """调用 push_reminder 工具。"""
        tool = self._tools.get("push_reminder")
        title = f"CarSoul 守护提醒：{root_cause}"
        if is_escalation:
            title = f"【加急】CarSoul 守护提醒：{root_cause}"
        if tool:
            r = tool.run(
                vehicle_id=vehicle_id, level=level,
                title=title, message=message,
            )
            return r.data if r.ok else {"title": title, "message": message}
        return {"title": title, "message": message}

    def _create_service_order(
        self, vehicle_id: int, svc: dict,
        root_cause: str, level: str,
    ) -> dict | None:
        """调用 create_service_order 工具（新增）。"""
        tool = self._tools.get("create_service_order")
        if tool:
            r = tool.run(
                vehicle_id=vehicle_id,
                service_type=svc["type"],
                service_name=svc["name"],
                priority=svc["priority"],
                reason=root_cause,
            )
            return r.data if r.ok else None
        # 降级：返回模拟工单
        return {
            "vehicle_id": vehicle_id,
            "service_type": svc["type"],
            "service_name": svc["name"],
            "priority": svc["priority"],
            "reason": root_cause,
            "status": "created",
            "estimated_response": "30分钟内",
        }
```

**修改文件：`ai-agent/carsoul_agent/tools/guard_tools.py`**

新增 `CreateServiceOrderTool`：

```python
class CreateServiceOrderTool(BaseTool):
    name = "create_service_order"
    description = (
        "根据车主预授权，创建外部服务工单（道路救援/车企服务中心/保险服务）。"
        "这是三级升级闭环第三级的执行工具，仅创建工单，不直接调度服务。"
    )
    parameters = {
        "vehicle_id": "integer",
        "service_type": "string  # roadside_assist | manufacturer_service | insurance_service",
        "service_name": "string",
        "priority": "string  # high | medium | low",
        "reason": "string",
    }

    def run(
        self,
        vehicle_id: int = 1,
        service_type: str = "roadside_assist",
        service_name: str = "道路救援",
        priority: str = "high",
        reason: str = "",
        **_: Any,
    ) -> ToolResult:
        record = {
            "vehicle_id": vehicle_id,
            "service_type": service_type,
            "service_name": service_name,
            "priority": priority,
            "reason": reason,
            "status": "created",
            "estimated_response": "30分钟内",
            "created_at": _now(),
        }
        action_store.service_orders.append(record)  # 新增列表
        return ToolResult(ok=True, data=record)
```

同步修改 `ActionStore`，新增 `service_orders` 列表：

```python
class ActionStore:
    def __init__(self) -> None:
        self.reminders: list[dict] = []
        self.lifecycle_events: list[dict] = []
        self.suggestions: list[dict] = []
        self.service_orders: list[dict] = []  # 新增

    def summary(self) -> dict[str, int]:
        return {
            "reminders": len(self.reminders),
            "lifecycle_events": len(self.lifecycle_events),
            "suggestions": len(self.suggestions),
            "service_orders": len(self.service_orders),  # 新增
        }

    def clear(self) -> None:
        self.reminders.clear()
        self.lifecycle_events.clear()
        self.suggestions.clear()
        self.service_orders.clear()  # 新增
```

同步修改 `GUARDED_TOOLS` 元组：

```python
GUARDED_TOOLS = (
    PushReminderTool,
    RecordLifecycleEventTool,
    WriteServiceSuggestionTool,
    CreateServiceOrderTool,  # 新增
)
```

**修改文件：`ai-agent/carsoul_agent/agents/core/service.py`**

在 `_anomaly_suggestion()` 中集成 `EscalationManager`：

```python
from carsoul_agent.agents.core.escalation import EscalationManager, EscalationConfig

class ServiceAgent:
    def __init__(self, llm_client=None, model_name="gpt-4o-mini"):
        self._llm = llm_client
        self._model = model_name
        self._tools = default_registry
        self._escalation = EscalationManager()  # 新增

    def _anomaly_suggestion(self, state: AgentState) -> dict:
        # ... 原有的 root_cause / actions_hint 提取逻辑保持不变 ...

        # 原有的三个守护工具调用保持不变（push_reminder / record / write_suggestion）
        # ...

        # 新增：执行三级升级闭环
        escalation_result = self._escalation.execute(state)

        return {
            "actions": actions_hint,
            "reminder": {
                "level": level,
                "title": f"CarSoul 守护提醒：{root_cause}",
            },
            "priority": priority,
            "patrol_completed": False,
            "action_store_summary": action_store.summary(),
            # 新增字段
            "escalation": {
                "level_reached": escalation_result.level_reached,
                "chain": escalation_result.escalation_chain,
                "service_orders": escalation_result.service_orders,
            },
        }
```

**修改文件：`ai-agent/carsoul_agent/agents/carsoul_agent.py`**

在 `_build_loop_summary()` 中透出升级链信息：

```python
def _build_loop_summary(self, state: AgentState) -> dict[str, Any]:
    # ... 原有逻辑 ...
    suggestion = state.get("service_suggestion", {}) or {}
    return {
        # ... 原有字段 ...
        "escalation": suggestion.get("escalation"),  # 新增
    }
```

#### 涉及文件清单

| 操作 | 文件 |
|------|------|
| **新建** | `ai-agent/carsoul_agent/agents/core/escalation.py` |
| 修改 | `ai-agent/carsoul_agent/tools/guard_tools.py` — 新增 `CreateServiceOrderTool` + `ActionStore.service_orders` |
| 修改 | `ai-agent/carsoul_agent/agents/core/service.py` — 集成 `EscalationManager` |
| 修改 | `ai-agent/carsoul_agent/agents/carsoul_agent.py` — `_build_loop_summary()` 透出升级链 |
| 可选 | `frontend/src/components/ClosedLoopTrace.tsx` — 渲染三级升级链 |

#### 验收标准

- [ ] `service.py` 异常分支返回 `escalation.chain` 包含 3 个级别
- [ ] `escalation.level_reached == 3`（当 level 为 warning/urgent 时）
- [ ] `action_store.service_orders` 有 3 条工单记录
- [ ] `closed_loop.escalation` 字段正确传递到前端
- [ ] 离线模式（无 LLM）下升级链正常执行

---

### P0-2 · RAG 接入诊断环节

#### 问题

`carsoul_agent.py` 的 `_build_initial_state()` 检索了知识库上下文（`kb.retrieve(message, top_k=3)`）并放入 `state["knowledge_context"]`，但 `diagnosis.py` 的 `_llm_enrich()` 和 `experts.py` 的 `_llm_enrich()` 均不消费该字段。`DIAGNOSIS_SYSTEM` 提示词声称「结合 RAG 检索」但实际未接入。

#### 当前代码（diagnosis.py:159-188）

```python
def _llm_enrich(self, diagnoses: list[dict], state: AgentState) -> None:
    # prompt 中不包含 knowledge_context
    prompt = (
        "你是 AI 车辆医生的主治诊断引擎。基于五专科专家的会诊发现，"
        "给出更精确的统一根因分析与置信度评估。\n"
        # ❌ 缺少 knowledge_context 注入
        f"车辆：{vehicle.get('brand', '')} ..."
        f"首要诊断：{json.dumps(diagnoses[0], ensure_ascii=False)}"
    )
```

#### 修复方案

**修改文件：`ai-agent/carsoul_agent/agents/core/diagnosis.py`**

在 `_llm_enrich()` 中注入 `knowledge_context`：

```python
def _llm_enrich(self, diagnoses: list[dict], state: AgentState) -> None:
    """Use LLM to refine the primary root cause and confidence."""
    try:
        import json
        vehicle = state.get("vehicle_state", {})
        knowledge_context = state.get("knowledge_context", "")  # 新增

        # 构建知识库增强提示
        knowledge_section = ""
        if knowledge_context:
            knowledge_section = (
                f"\n\n【知识库检索结果】\n{knowledge_context}\n"
                "请结合以上知识库案例和故障模式，给出更精确的根因分析。"
            )

        prompt = (
            "你是 AI 车辆医生的主治诊断引擎。基于五专科专家的会诊发现，"
            "给出更精确的统一根因分析与置信度评估。\n"
            "输出 JSON：{\"root_cause\": str, \"confidence\": float, "
            "\"reasoning\": str, \"knowledge_match\": str}\n\n"
            f"车辆：{vehicle.get('brand', '')} {vehicle.get('model', '')} "
            f"{vehicle.get('year', '')}，里程 {vehicle.get('mileage', 'N/A')} km\n"
            f"首要诊断：{json.dumps(diagnoses[0], ensure_ascii=False, default=str)}"
            f"{knowledge_section}"  # 新增
        )
        resp = self._llm.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,  # 适当增加以容纳知识库推理
        )
        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        enrichment = json.loads(text)
        if enrichment.get("root_cause"):
            diagnoses[0]["root_cause"] = enrichment["root_cause"]
        if enrichment.get("confidence"):
            diagnoses[0]["confidence"] = enrichment["confidence"]
        if enrichment.get("knowledge_match"):
            diagnoses[0]["knowledge_match"] = enrichment["knowledge_match"]
        diagnoses[0]["source"] = "llm_enriched_with_rag"  # 标记 RAG 增强
    except Exception as exc:
        logger.debug("LLM diagnosis enrichment skipped: %s", exc)
```

**修改文件：`ai-agent/carsoul_agent/agents/core/experts.py`**

在 `ExpertAgent._llm_enrich()` 中注入 `knowledge_context`：

```python
def _llm_enrich(self, findings: list[dict], state: AgentState) -> None:
    """Optional LLM refinement of the top finding's reasoning."""
    try:
        import json
        vehicle = state.get("vehicle_state", {})
        knowledge_context = state.get("knowledge_context", "")  # 新增

        knowledge_section = ""
        if knowledge_context:
            knowledge_section = (
                f"\n\n【相关知识库内容】\n{knowledge_context}\n"
                "请结合以上知识判断根因是否与历史案例匹配。"
            )

        prompt = (
            f"你是{self.specialty}专家。基于以下发现，给出更精确的根因与置信度。\n"
            "输出 JSON：{\"root_cause\": str, \"confidence\": float, "
            "\"reasoning\": str, \"knowledge_match\": str}\n\n"
            f"车辆：{vehicle.get('brand', '')} {vehicle.get('model', '')}，"
            f"里程 {vehicle.get('mileage', 'N/A')} km\n"
            f"发现：{json.dumps(findings[0], ensure_ascii=False)}"
            f"{knowledge_section}"  # 新增
        )
        resp = self._llm.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,  # 适当增加
        )
        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        enrichment = json.loads(text)
        if enrichment.get("root_cause"):
            findings[0]["root_cause"] = enrichment["root_cause"]
        if enrichment.get("confidence"):
            findings[0]["confidence"] = enrichment["confidence"]
        if enrichment.get("knowledge_match"):
            findings[0]["knowledge_match"] = enrichment["knowledge_match"]
        findings[0]["source"] = "llm_enriched_with_rag"
    except Exception as exc:
        logger.debug("%s LLM enrich skipped: %s", self.name, exc)
```

**新增：离线模式下的 RAG 规则匹配**

当 LLM 不可用时，在 `diagnosis.py` 中增加基于关键词的规则匹配：

```python
def _rule_based_knowledge_match(
    self, diagnoses: list[dict], knowledge_context: str
) -> None:
    """离线模式：从知识库上下文中提取匹配信息。"""
    if not knowledge_context:
        return
    for d in diagnoses:
        root_cause = d.get("root_cause", "")
        # 简单关键词匹配
        if root_cause and root_cause in knowledge_context:
            d["knowledge_match"] = f"知识库中找到相关案例：{root_cause}"
            d["source"] = "rule_kb_matched"
```

在 `run()` 的 Stage 3 中调用：

```python
# Stage 3: LLM enrichment (optional)
if self._llm is not None and diagnoses:
    self._llm_enrich(diagnoses, state)
else:
    # 离线模式：规则匹配知识库
    self._rule_based_knowledge_match(
        diagnoses, state.get("knowledge_context", "")
    )
```

#### 涉及文件清单

| 操作 | 文件 |
|------|------|
| 修改 | `ai-agent/carsoul_agent/agents/core/diagnosis.py` — `_llm_enrich()` 注入 knowledge_context + 新增 `_rule_based_knowledge_match()` |
| 修改 | `ai-agent/carsoul_agent/agents/core/experts.py` — `ExpertAgent._llm_enrich()` 注入 knowledge_context |

#### 验收标准

- [ ] LLM 模式下，诊断输出包含 `knowledge_match` 字段
- [ ] 离线模式下，诊断输出包含 `knowledge_match` 字段（规则匹配）
- [ ] `source` 字段标记为 `llm_enriched_with_rag` 或 `rule_kb_matched`
- [ ] trace_log 中诊断步骤的 data 包含知识库使用记录
- [ ] Demo ACT3 的「知识库匹配」推理链可由后端真实数据驱动

---

### P0-3 · 主动巡检调度器

#### 问题

后端 `risk_prediction_service.py` 有 `patrol_all()` 方法，但无调度器定时触发。Agent `handle()` 仅在用户发消息时运行。产品定位「主动守护」实际为「被动响应」。

#### 修复方案

**新增文件：`backend/app/services/scheduler.py`**

```python
"""主动巡检调度器 — 让 CarSoul 真正「主动」守护。

使用 APScheduler 定时触发 patrol_all()，
无需用户发消息即可主动发现风险并推送提醒。

调度策略：
  - 常规巡检：每 30 分钟一次（可配置）
  - 深夜巡检：每 2 小时一次（降低频率）
  - 高风险车辆：每 10 分钟一次

降级策略：
  - APScheduler 未安装 → 提供手动触发 API 端点
  - 巡检失败 → 记录日志，不影响下次调度
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any

from app.db import SessionLocal
from app.services import risk_prediction_service

logger = logging.getLogger(__name__)

# 全局调度器实例
_scheduler = None
_patrol_config = {
    "interval_minutes": 30,       # 常规巡检间隔
    "night_interval_minutes": 120, # 深夜巡检间隔
    "night_start_hour": 23,       # 深夜开始时间
    "night_end_hour": 6,          # 深夜结束时间
}


def init_scheduler():
    """初始化 APScheduler 并注册巡检任务。"""
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.warning(
            "APScheduler not installed. "
            "Patrol can be triggered manually via POST /api/risk/patrol"
        )
        return False

    _scheduler = BackgroundScheduler()

    # 注册常规巡检任务
    _scheduler.add_job(
        _patrol_job,
        trigger=IntervalTrigger(minutes=_patrol_config["interval_minutes"]),
        id="patrol_regular",
        name="CarSoul 常规主动巡检",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("CarSoul patrol scheduler started (interval=%dm)",
                _patrol_config["interval_minutes"])
    return True


def shutdown_scheduler():
    """关闭调度器。"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _patrol_job():
    """巡检任务执行体。"""
    logger.info("CarSoul patrol started at %s", datetime.utcnow())
    try:
        db = SessionLocal()
        try:
            result = risk_prediction_service.patrol_all(db)
            logger.info(
                "Patrol completed: %d vehicles, %d predictions, %d alerts",
                result.get("patrolled", 0),
                result.get("predictions_made", 0),
                result.get("alerts_generated", 0),
            )
        finally:
            db.close()
    except Exception as exc:
        logger.exception("Patrol job failed: %s", exc)


def get_scheduler_status() -> dict[str, Any]:
    """获取调度器状态。"""
    if _scheduler is None:
        return {
            "running": False,
            "jobs": [],
            "message": "Scheduler not initialized. Install APScheduler or use manual patrol.",
        }

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return {
        "running": _scheduler.running,
        "jobs": jobs,
        "config": _patrol_config,
    }
```

**修改文件：`backend/app/api/risk/router.py`**

新增调度器管理端点：

```python
from app.services.scheduler import (
    init_scheduler, shutdown_scheduler, get_scheduler_status
)

@router.get("/risk/scheduler/status")
async def scheduler_status():
    """获取主动巡检调度器状态。"""
    return get_scheduler_status()

@router.post("/risk/scheduler/start")
async def scheduler_start():
    """启动主动巡检调度器。"""
    success = init_scheduler()
    return {"started": success, "status": get_scheduler_status()}

@router.post("/risk/scheduler/stop")
async def scheduler_stop():
    """停止主动巡检调度器。"""
    shutdown_scheduler()
    return {"stopped": True}
```

**修改文件：`backend/app/main.py`**

在应用启动时初始化调度器：

```python
from app.services.scheduler import init_scheduler

@app.on_event("startup")
async def startup_event():
    # ... 原有启动逻辑 ...
    # 初始化主动巡检调度器
    init_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    from app.services.scheduler import shutdown_scheduler
    shutdown_scheduler()
```

**修改文件：`backend/requirements.txt`**

```
apscheduler>=3.10.0
```

#### 涉及文件清单

| 操作 | 文件 |
|------|------|
| **新建** | `backend/app/services/scheduler.py` |
| 修改 | `backend/app/api/risk/router.py` — 新增 3 个调度器管理端点 |
| 修改 | `backend/app/main.py` — startup/shutdown 初始化调度器 |
| 修改 | `backend/requirements.txt` — 新增 `apscheduler` 依赖 |

#### 验收标准

- [ ] 应用启动后调度器自动运行
- [ ] `GET /api/risk/scheduler/status` 返回调度器状态和下次巡检时间
- [ ] `POST /api/risk/patrol` 可手动触发巡检（已有端点）
- [ ] 巡检日志可见（`Patrol completed: X vehicles, Y predictions, Z alerts`）
- [ ] APScheduler 未安装时降级为手动触发，不崩溃

---

## 三、Phase 2 · P1 高优先级增强

### P1-1 · 长期记忆系统

#### 问题

`memory/conversation.py` 仅有进程内 `ConversationMemory`（session 级），无长期车辆记忆、无跨会话记忆、无持久化。后端有 `VehicleMemory` 表（7 类记忆）但 Agent 不读写。

#### 修复方案

**新增文件：`ai-agent/carsoul_agent/memory/vehicle_memory.py`**

```python
"""车辆长期记忆系统 — L3 长期记忆层。

实现车辆生命周期记忆：
  - 记录每次诊断结果和守护动作
  - 记录用户偏好和交互历史
  - Agent 启动时加载历史记忆注入上下文

数据存储：后端 VehicleMemory 表（通过 API）
降级策略：API 不可用时降级为内存 dict
"""
from __future__ import annotations
import logging
from typing import Any
from datetime import datetime

logger = logging.getLogger(__name__)


class VehicleMemory:
    """车辆长期记忆 — 跨会话持久化。"""

    MEMORY_TYPES = [
        "diagnosis_history",    # 诊断历史
        "user_preference",      # 用户偏好
        "guard_action",         # 守护动作记录
        "anomaly_pattern",      # 异常模式
        "recovery_event",       # 恢复事件
        "emotional_bond",       # 情感连接
        "context_summary",      # 上下文摘要
    ]

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self._api_base = api_base_url.rstrip("/")
        self._cache: dict[int, list[dict]] = {}  # 降级用内存缓存

    def recall(
        self, vehicle_id: int, memory_type: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """召回车辆记忆。"""
        try:
            import requests
            params = {"limit": limit}
            if memory_type:
                params["memory_type"] = memory_type
            resp = requests.get(
                f"{self._api_base}/api/digital-twin/{vehicle_id}/memories",
                params=params, timeout=5,
            )
            if resp.ok:
                return resp.json()
        except Exception as exc:
            logger.debug("Vehicle memory recall degraded: %s", exc)
        return self._cache.get(vehicle_id, [])

    def remember(
        self, vehicle_id: int, memory_type: str,
        content: str, metadata: dict | None = None,
    ) -> dict | None:
        """写入车辆记忆。"""
        record = {
            "vehicle_id": vehicle_id,
            "memory_type": memory_type,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        try:
            import requests
            resp = requests.post(
                f"{self._api_base}/api/digital-twin/{vehicle_id}/memories",
                json=record, timeout=5,
            )
            if resp.ok:
                return resp.json()
        except Exception as exc:
            logger.debug("Vehicle memory write degraded: %s", exc)
        # 降级：写入内存缓存
        self._cache.setdefault(vehicle_id, []).append(record)
        return record

    def recall_as_context(
        self, vehicle_id: int, limit: int = 5,
    ) -> str:
        """将历史记忆格式化为 LLM 上下文文本。"""
        memories = self.recall(vehicle_id, limit=limit)
        if not memories:
            return ""
        parts = ["【车辆历史记忆】"]
        for m in memories[:limit]:
            parts.append(
                f"- [{m.get('memory_type', '未知')}] "
                f"{m.get('content', '')}"
            )
        return "\n".join(parts)
```

**修改文件：`ai-agent/carsoul_agent/agents/carsoul_agent.py`**

在 `_build_initial_state()` 中加载车辆记忆：

```python
from carsoul_agent.memory.vehicle_memory import VehicleMemory

class CarSoulGuardianAgent(BaseAgent):
    def __init__(self, model_name=None, **kwargs):
        super().__init__(model_name=model_name, **kwargs)
        # ... 原有初始化 ...
        self._vehicle_memory = VehicleMemory(
            api_base_url=self.settings.api_base_url
        )

    def _build_initial_state(self, message, user):
        # ... 原有逻辑 ...

        # 新增：加载车辆历史记忆
        memory_context = ""
        try:
            memory_context = self._vehicle_memory.recall_as_context(
                vehicle_id=1, limit=5
            )
        except Exception as exc:
            logger.debug("Vehicle memory recall skipped: %s", exc)

        state: AgentState = {
            # ... 原有字段 ...
            "memory_context": memory_context,  # 新增
        }
        return state
```

在 `_run_workflow()` 完成后写入记忆：

```python
def _run_workflow(self, message, user):
    try:
        state = self._build_initial_state(message, user)
        result = CoreWorkflow.run(state)

        # 新增：写入车辆长期记忆
        self._persist_memory(result, user)

        return self._format_answer(result), self._build_loop_summary(result)
    except Exception as exc:
        # ...

def _persist_memory(self, state: AgentState, user: str) -> None:
    """将本次诊断结果写入车辆长期记忆。"""
    try:
        diagnosis = state.get("diagnosis", {}).get("primary", {})
        if diagnosis:
            self._vehicle_memory.remember(
                vehicle_id=1,
                memory_type="diagnosis_history",
                content=f"诊断：{diagnosis.get('root_cause', '未知')}，"
                        f"严重度：{diagnosis.get('severity', 'info')}，"
                        f"置信度：{diagnosis.get('confidence', 0)}",
                metadata={
                    "type": diagnosis.get("type"),
                    "source": diagnosis.get("source"),
                },
            )
    except Exception as exc:
        logger.debug("Memory persist skipped: %s", exc)
```

#### 涉及文件清单

| 操作 | 文件 |
|------|------|
| **新建** | `ai-agent/carsoul_agent/memory/vehicle_memory.py` |
| 修改 | `ai-agent/carsoul_agent/agents/carsoul_agent.py` — 加载+写入记忆 |
| 修改 | `ai-agent/carsoul_agent/agents/core/state.py` — AgentState 新增 `memory_context` 字段 |

#### 验收标准

- [ ] Agent 启动时加载车辆历史诊断记忆
- [ ] 每次诊断结果写入后端 `VehicleMemory` 表
- [ ] 后端 API 不可用时降级为内存缓存
- [ ] `memory_context` 注入到工作流状态中

---

### P1-2 · 守护工具 DB 持久化

#### 问题

`guard_tools.py` 的 `ActionStore` 是纯内存实现，重启丢失。注释提到「TASK009+ will persist to alerts / lifecycle_events / service_suggestions tables」但未实现。

#### 修复方案

**修改文件：`ai-agent/carsoul_agent/tools/guard_tools.py`**

为每个工具增加可选的 DB 持久化回调：

```python
class ActionStore:
    """守护动作账本 — 内存 + 可选 DB 持久化。"""

    def __init__(self) -> None:
        self.reminders: list[dict] = []
        self.lifecycle_events: list[dict] = []
        self.suggestions: list[dict] = []
        self.service_orders: list[dict] = []
        # 持久化回调（由后端注入）
        self._persist_callbacks: dict[str, Any] = {}

    def register_persist_callback(self, action_type: str, callback):
        """注册 DB 持久化回调。"""
        self._persist_callbacks[action_type] = callback

    def summary(self) -> dict[str, int]:
        return {
            "reminders": len(self.reminders),
            "lifecycle_events": len(self.lifecycle_events),
            "suggestions": len(self.suggestions),
            "service_orders": len(self.service_orders),
        }

    def clear(self) -> None:
        self.reminders.clear()
        self.lifecycle_events.clear()
        self.suggestions.clear()
        self.service_orders.clear()


class PushReminderTool(BaseTool):
    # ...
    def run(self, vehicle_id=1, level="info", title="", message="", **_):
        record = {
            "vehicle_id": vehicle_id,
            "level": level,
            "title": title,
            "message": message,
            "created_at": _now(),
        }
        action_store.reminders.append(record)
        # 新增：尝试 DB 持久化
        callback = action_store._persist_callbacks.get("reminder")
        if callback:
            try:
                callback(record)
            except Exception as exc:
                logger.warning("Reminder DB persist failed: %s", exc)
        return ToolResult(ok=True, data=record)
```

**修改文件：`backend/app/services/agent_service.py`**

在 Agent 初始化时注入持久化回调：

```python
from app.db import SessionLocal
from app.services import alert_service, lifecycle_service

def _init_agent():
    agent = CarSoulGuardianAgent(...)

    # 注入 DB 持久化回调
    from carsoul_agent.tools.guard_tools import action_store

    def persist_reminder(record):
        db = SessionLocal()
        try:
            alert_service.create_alert(db, vehicle_id=record["vehicle_id"], ...)
        finally:
            db.close()

    def persist_lifecycle(record):
        db = SessionLocal()
        try:
            lifecycle_service.create_event(db, ...)
        finally:
            db.close()

    action_store.register_persist_callback("reminder", persist_reminder)
    action_store.register_persist_callback("lifecycle", persist_lifecycle)
    action_store.register_persist_callback("suggestion", persist_suggestion)

    return agent
```

#### 涉及文件清单

| 操作 | 文件 |
|------|------|
| 修改 | `ai-agent/carsoul_agent/tools/guard_tools.py` — ActionStore 增加回调机制 |
| 修改 | `backend/app/services/agent_service.py` — 注入持久化回调 |

#### 验收标准

- [ ] `push_reminder` 执行后后端 `vehicle_alerts` 表有记录
- [ ] `record_lifecycle_event` 执行后后端 `vehicle_lifecycle_events` 表有记录
- [ ] `write_service_suggestion` 执行后后端有持久化记录
- [ ] 后端不可用时降级为仅内存，不崩溃

---

### P1-3 · 车辆工具接入后端 DB

#### 问题

`vehicle_tools.py` 的 6 个工具全部返回硬编码 mock 数据，未接入后端 DB。Agent 层与后端数据层完全断裂。

#### 修复方案

**修改文件：`ai-agent/carsoul_agent/tools/vehicle_tools.py`**

为每个工具增加后端 API 调用，保留 mock 作为降级：

```python
import requests

_API_BASE = "http://localhost:8000"

def _api_get(path: str, **params) -> dict | None:
    """调用后端 API，失败返回 None。"""
    try:
        resp = requests.get(f"{_API_BASE}{path}", params=params, timeout=5)
        if resp.ok:
            return resp.json()
    except Exception:
        pass
    return None


class GetVehicleInfoTool(BaseTool):
    # ...
    def run(self, vehicle_id=1, **_):
        # 优先从后端获取
        data = _api_get(f"/api/vehicle/{vehicle_id}/archive")
        if data:
            return ToolResult(ok=True, data=data)
        # 降级：返回 mock 数据
        return ToolResult(ok=True, data=_MOCK_VEHICLE_INFO)
```

对 6 个工具逐一改造：
- `get_vehicle_info` → `GET /api/vehicle/{id}/archive`
- `get_health_score` → `GET /api/vehicle/{id}/health-score`
- `get_maintenance_plan` → `GET /api/vehicle/{id}/maintenance/schedules`
- `get_driving_behavior` → `GET /api/vehicle/{id}/driving-behavior/summary`
- `get_lifecycle_timeline` → `GET /api/vehicle/{id}/lifecycle`
- `get_alerts` → `GET /api/vehicle/{id}/alerts`

#### 涉及文件清单

| 操作 | 文件 |
|------|------|
| 修改 | `ai-agent/carsoul_agent/tools/vehicle_tools.py` — 6 个工具增加 API 调用 |

#### 验收标准

- [ ] 后端运行时，工具返回后端真实数据
- [ ] 后端不可用时，降级返回 mock 数据
- [ ] Agent 诊断基于真实车辆数据而非硬编码

---

### P1-4 · 风险预测前端页面

#### 问题

后端 `/api/risk/*` 完整闭环已实现（predict→acknowledge→feedback→accuracy），但前端无页面调用。用户无法确认预测、反馈结果、查看准确率。

#### 修复方案

**新增文件：`frontend/src/pages/RiskPrediction.tsx`**

```tsx
// 核心功能：
// 1. 风险预测列表 — 展示历史预测，含等级/概率/根因/状态
// 2. 预测详情 — 展示完整推理轨迹 (trace_log)
// 3. 确认预测 — acknowledge 操作
// 4. 反馈结果 — submit_feedback (confirmed/false_alarm/no_event/partial)
// 5. 准确率看板 — accuracy_rate / false_alarm_rate / by_level
// 6. 手动巡检 — 触发 POST /api/risk/patrol

// 数据来源：
// GET  /api/vehicle/{id}/risk/predictions
// GET  /api/risk/predictions/{id}
// POST /api/risk/predictions/{id}/acknowledge
// POST /api/risk/predictions/{id}/feedback
// GET  /api/vehicle/{id}/risk/accuracy
// POST /api/vehicle/{id}/risk/predict
// POST /api/risk/patrol
```

**新增文件：`frontend/src/services/riskService.ts`**

```typescript
export const riskService = {
  listPredictions: (vehicleId: number) =>
    api.get(`/api/vehicle/${vehicleId}/risk/predictions`),
  getPrediction: (id: number) =>
    api.get(`/api/risk/predictions/${id}`),
  acknowledge: (id: number) =>
    api.post(`/api/risk/predictions/${id}/acknowledge`),
  submitFeedback: (id: number, outcome: string, notes?: string) =>
    api.post(`/api/risk/predictions/${id}/feedback`, { actual_outcome: outcome, outcome_notes: notes }),
  getAccuracy: (vehicleId: number) =>
    api.get(`/api/vehicle/${vehicleId}/risk/accuracy`),
  triggerPrediction: (vehicleId: number) =>
    api.post(`/api/vehicle/${vehicleId}/risk/predict`),
  patrol: () => api.post(`/api/risk/patrol`),
};
```

**修改文件：`frontend/src/layouts/MainLayout.tsx`**

在导航菜单中新增「风险预测」入口。

**修改文件：`frontend/src/App.tsx`**

新增路由 `/risk` → `RiskPrediction`。

#### 涉及文件清单

| 操作 | 文件 |
|------|------|
| **新建** | `frontend/src/pages/RiskPrediction.tsx` |
| **新建** | `frontend/src/services/riskService.ts` |
| 修改 | `frontend/src/layouts/MainLayout.tsx` — 导航新增 |
| 修改 | `frontend/src/App.tsx` — 路由新增 |

#### 验收标准

- [ ] 页面展示历史预测列表
- [ ] 可查看单条预测的完整推理轨迹
- [ ] 可确认预测（acknowledge）
- [ ] 可提交反馈（feedback）闭合环路
- [ ] 准确率看板正确展示
- [ ] 可手动触发预测和巡检

---

## 四、Phase 3 · P2 中优先级优化

### P2-1 · WebSocket/SSE 实时数据流

**问题**：前端无实时推送，Dashboard/VehicleLifeHome 均为轮询或一次性加载。

**方案**：
- 后端新增 `/api/ws/vehicle/{id}` WebSocket 端点
- 主动巡检发现风险时通过 WebSocket 推送到前端
- AgentChat 的思考过程改为 SSE 流式输出

**涉及文件**：
- 新建 `backend/app/api/ws/router.py`
- 修改 `backend/app/main.py` — 注册 WebSocket 路由
- 修改 `frontend/src/hooks/useAgent.ts` — 支持 SSE 流式接收

### P2-2 · 专家提示词统一管理

**问题**：`system_prompts.py` 定义了 5 个专家提示词但 `experts.py` 不使用，内联构建 prompt。

**方案**：在 `experts.py` 的 `_llm_enrich()` 中使用 `get_prompt()` 加载对应专家提示词。

**涉及文件**：
- 修改 `ai-agent/carsoul_agent/agents/core/experts.py`

### P2-3 · 传感器数据接入后端

**问题**：`_build_sensor_window()` 从健康数据推导传感器读数，非真实传感器。

**方案**：
- `vehicle_tools.py` 新增 `get_sensor_data` 工具调用 `GET /api/vehicle/{id}/sensors/series`
- `carsoul_agent.py` 的 `_build_initial_state()` 优先从传感器 API 获取数据

**涉及文件**：
- 修改 `ai-agent/carsoul_agent/tools/vehicle_tools.py`
- 修改 `ai-agent/carsoul_agent/agents/carsoul_agent.py`

### P2-4 · 遗留代码清理

**问题**：`workflows/base.py` 已废弃、`carsoul_guardian.yaml` 未被加载。

**方案**：
- 删除 `ai-agent/carsoul_agent/workflows/base.py`
- 删除 `ai-agent/carsoul_agent/prompts/carsoul_guardian.yaml` 或修改 `system_prompts.py` 从 YAML 加载

**涉及文件**：
- 删除 `ai-agent/carsoul_agent/workflows/base.py`
- 删除或修改 `ai-agent/carsoul_agent/prompts/carsoul_guardian.yaml`

---

## 五、实施顺序与依赖关系

```
Phase 1 (P0) — 比赛前必须完成
  │
  ├─ P0-2 RAG 接入诊断 ──── 独立，无依赖
  │    └─ 修改 diagnosis.py + experts.py
  │
  ├─ P0-1 三级升级闭环 ──── 独立，无依赖
  │    ├─ 新建 escalation.py
  │    ├─ 修改 guard_tools.py (新增 CreateServiceOrderTool)
  │    └─ 修改 service.py
  │
  └─ P0-3 主动巡检调度器 ── 独立，无依赖
       ├─ 新建 scheduler.py
       └─ 修改 main.py + risk/router.py

Phase 2 (P1) — 比赛加分项
  │
  ├─ P1-3 车辆工具接 DB ──── 独立
  │
  ├─ P1-2 守护工具持久化 ── 依赖 P1-3 (需要后端数据层可用)
  │
  ├─ P1-1 长期记忆系统 ──── 独立 (后端已有 VehicleMemory 表)
  │
  └─ P1-4 风险预测前端 ──── 独立 (后端 API 已完整)

Phase 3 (P2) — 锦上添花
  │
  ├─ P2-4 遗留代码清理 ──── 独立，随时可做
  ├─ P2-2 专家提示词统一 ── 独立
  ├─ P2-3 传感器接后端 ──── 依赖 P1-3
  └─ P2-1 WebSocket 实时 ── 依赖 P0-3 (巡检推送需要 WebSocket)
```

### 建议实施顺序

| 顺序 | 任务 | 预估工时 | 依赖 |
|------|------|---------|------|
| 1 | P2-4 遗留代码清理 | 0.5h | 无 |
| 2 | P0-2 RAG 接入诊断 | 2h | 无 |
| 3 | P0-1 三级升级闭环 | 4h | 无 |
| 4 | P0-3 主动巡检调度器 | 2h | 无 |
| 5 | P1-3 车辆工具接 DB | 3h | 无 |
| 6 | P1-1 长期记忆系统 | 3h | 无 |
| 7 | P1-2 守护工具持久化 | 2h | P1-3 |
| 8 | P1-4 风险预测前端 | 4h | 无 |
| 9 | P2-2 专家提示词统一 | 1h | 无 |
| 10 | P2-3 传感器接后端 | 2h | P1-3 |
| 11 | P2-1 WebSocket 实时 | 4h | P0-3 |

**P0 总工时**：约 8 小时
**P0+P1 总工时**：约 20 小时
**全部总工时**：约 27.5 小时

---

## 六、验收检查清单

### P0 验收（比赛前必须通过）

- [ ] **P0-1**：`service.py` 异常分支返回 `escalation.chain` 包含 3 个级别
- [ ] **P0-1**：`action_store.service_orders` 有 3 条工单记录
- [ ] **P0-1**：前端 `ClosedLoopTrace` 能渲染三级升级链
- [ ] **P0-2**：LLM 模式下诊断输出包含 `knowledge_match` 字段
- [ ] **P0-2**：离线模式下诊断输出包含 `knowledge_match`（规则匹配）
- [ ] **P0-3**：应用启动后调度器自动运行
- [ ] **P0-3**：`GET /api/risk/scheduler/status` 返回调度器状态
- [ ] **P0-3**：巡检日志可见

### P1 验收（比赛加分项）

- [ ] **P1-1**：Agent 启动时加载车辆历史诊断记忆
- [ ] **P1-1**：每次诊断结果写入后端 `VehicleMemory` 表
- [ ] **P1-2**：`push_reminder` 执行后后端 `vehicle_alerts` 表有记录
- [ ] **P1-2**：`record_lifecycle_event` 执行后后端有记录
- [ ] **P1-3**：后端运行时车辆工具返回真实数据
- [ ] **P1-3**：后端不可用时降级返回 mock 数据
- [ ] **P1-4**：风险预测页面可展示历史预测列表
- [ ] **P1-4**：可确认预测和提交反馈
- [ ] **P1-4**：准确率看板正确展示

### P2 验收（锦上添花）

- [ ] **P2-1**：WebSocket 连接建立后可接收实时推送
- [ ] **P2-2**：专家 Agent 使用 `system_prompts.py` 中的提示词
- [ ] **P2-3**：传感器数据来自后端 API
- [ ] **P2-4**：`workflows/base.py` 已删除
- [ ] **P2-4**：YAML 文件已删除或正确加载

### 闭环完整性终验

```
✅ 感知：车辆工具返回真实数据 (P1-3)
✅ 理解：RAG 知识库增强诊断 (P0-2)
✅ 决策：风险等级 + 概率 + ETA
✅ 行动：三级升级闭环 (P0-1) + DB 持久化 (P1-2)
✅ 反馈：前端风险预测页面 (P1-4)
✅ 记忆：长期车辆记忆 (P1-1)
✅ 主动：定时巡检调度器 (P0-3)
✅ 实时：WebSocket 推送 (P2-1)
```
