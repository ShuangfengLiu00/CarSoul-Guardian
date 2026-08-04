# CarSoul Guardian — AI Agent 模块

CarSoul Guardian 的独立 AI Agent 层。**AI 逻辑只存在于此模块，不写在后端接口里**，保证可扩展、可替换、支持未来多 Agent。

## 定位

> AI 车辆医生 + 多智能体车辆专家系统 + 车辆数字生命档案

像一位「主治医生」守护车辆：先采集体征（感知），再召集五位专科专家并行会诊，最后给出诊断报告与处方随访。不是普通的车载问答机器人，而是拥有车辆数字生命档案、主动守护车辆健康的 AI 车辆医生。

## 目录结构

```
ai-agent/
├── carsoul_agent/                   # 可被后端 import 的 Python 包
│   ├── agents/
│   │   ├── base.py                  # BaseAgent 统一接口
│   │   ├── registry.py              # Agent 注册表（支持多Agent）
│   │   ├── carsoul_agent.py         # CarSoulGuardianAgent 主守护Agent（AI车辆医生，编排五子Agent）
│   │   └── core/                    # ★ TASK008 五子 Agent + 多智能体专家会诊 + 状态图工作流
│   │       ├── __init__.py
│   │       ├── state.py             # AgentState 共享状态 + Trace 追踪（含 expert_opinions）
│   │       ├── perception.py        # ① 问诊·体征采集 Agent
│   │       ├── diagnosis.py         # ② 专家会诊中枢（召集五专家并行会诊 + 汇总诊断）
│   │       ├── experts.py           # ★ 多智能体专家面板（五专科专家）
│   │       ├── risk.py              # ③ 风险分级 Agent
│   │       ├── explainer.py         # ④ 诊断报告 Agent（画像适配语言）
│   │       ├── service.py           # ⑤ 处方·随访 Agent（守护工具层）
│   │       └── workflow.py          # StateGraph 状态图编排
│   ├── prompts/                     # 提示词管理（12 个 Prompt：主Agent + 五子Agent + 五专家）
│   ├── tools/
│   │   ├── base.py                  # Tool 基类 + 注册表
│   │   ├── vehicle_tools.py         # 6 个读工具（车辆/健康/保养/行为/生命周期/告警）
│   │   └── guard_tools.py           # ★ 3 个守护工具（推送提醒/记录生命周期/写入建议）
│   ├── memory/                      # 记忆层（对话记忆 + 向量库预留）
│   ├── workflows/                   # 工作流基类（预留）
│   └── config/                      # Agent 配置
├── tests/
│   └── test_agent.py                # 23 个测试（含五子Agent闭环 + 专家会诊 + Trace + 守护边界）
├── requirements.txt
└── pyproject.toml
```

## 核心 Agent：CarSoulGuardianAgent

主守护 Agent（AI 车辆医生）是用户-facing 入口，编排五子 Agent 工作流：

```
用户消息 → 收集车辆状态 → CoreWorkflow → 专家会诊 + 诊断报告 + 处方随访 + Trace
```

五项职责：
1. 问诊·体征采集 — 通过工具收集车辆数字生命档案数据
2. 专家会诊 — 召集五位专科专家并行诊断，汇总成统一会诊结论
3. 诊断报告 — 返回解释 Agent 的用户语言输出（标注会诊来源）
4. 处方随访 — 服务 Agent 触发守护工具推送提醒
5. 推理可追溯 — 全程 Trace 记录，每个步骤可审计

## 三条红线（不可违反）
1. 不是聊天机器人——每次回答落到具体车辆状态/数据/建议
2. 必须闭环——分析→建议→行动→追踪
3. 守护非控制——只给建议与提醒，绝不替用户执行不可逆操作

## 诊疗闭环（TASK008 — AI 车辆医生 · 多智能体专家会诊）

### 状态图拓扑

```
START → perception(问诊) → {is_normal?}
                                │ no  → diagnosis(专家会诊) → risk(分级) → explainer(报告) → service(处方) → END
                                │ yes → explainer(巡检报告) → service → END
```

### 五子 Agent 职责（诊疗闭环）

| # | Agent | 诊疗角色 | 职责 | 离线模式 | LLM增强 |
|---|-------|----------|------|----------|---------|
| ① | perception | 问诊·体征采集 | 阈值检测 + 语义异常识别 | 规则引擎（8条阈值） | 语义趋势检测 |
| ② | diagnosis | 专家会诊中枢 | 召集五专家并行会诊 + 汇总诊断 | 7种故障模式知识库 + 专家面板 | 根因增强 + 置信度 |
| ③ | risk | 风险分级 | 风险量化（等级/概率/ETA） | 严重度映射表 | — |
| ④ | explainer | 诊断报告 | 按驾驶画像适配语言 | 模板生成（3种风格） | 自然语言生成 |
| ⑤ | service | 处方·随访 | 推送提醒 + 记录 + 建议 | 守护工具调用 | — |

### 多智能体专家面板（五专科专家会诊）

诊断节点（diagnosis）作为会诊中枢，召集五位专科专家并行诊断，每位专家只负责自己领域：

| 专家 | 专科 | 关注领域 | 核心能力 |
|------|------|----------|----------|
| PowertrainExpert | 动力系统 | 电池/发动机/电机 | 热失控征兆、电量损耗、过热检测 |
| ChassisExpert | 底盘系统 | 刹车/轮胎/悬挂 | 磨损极限、高里程老化、制动安全 |
| ElectricalExpert | 电气系统 | 传感器/电路/电子 | 故障码排查、传感器误报排除 |
| DrivingBehaviorExpert | 驾驶行为 | 习惯/安全评分 | 激烈驾驶风险、安全评分预警 |
| MaintenanceExpert | 保养规划 | 周期/成本/优先级 | 保养节点、健康衰退、优先级排序 |

每位专家输出结构化会诊意见（findings / severity / recommendation / confidence），由诊断中枢汇总成统一诊断结论。专家相互隔离，单个专家失败不影响其余会诊。

### 守护工具层（工具层闸门）

服务 Agent 只能调用 3 个守护工具，**不存在任何控制执行器的工具**：

| 工具 | 功能 | 边界 |
|------|------|------|
| `push_reminder` | 推送主动守护提醒 | 仅提醒 |
| `record_lifecycle_event` | 记录生命周期事件 | 仅记录 |
| `write_service_suggestion` | 持久化服务建议 | 仅写入建议 |

所有调用记录在 `ActionStore` 中，可供评委审计验证「无控制动作」。

### GOAI 闭环五步

| 步骤 | Trace标记 | 落点Agent |
|------|-----------|-----------|
| 感知 | `step=perceive` | perception |
| 理解 | `step=understand` | diagnosis（含专家会诊） |
| 推理 | `step=reason` | diagnosis/risk |
| 调用工具 | `step=tool` | explainer |
| 执行任务 | `step=act` | service |

## 运行机制
- 配置 `OPENAI_API_KEY` 时：五子 Agent + 五专科专家使用 LLM 做语义检测、根因增强、自然语言生成
- 未配置时：全部走规则引擎 + 专家知识库，保证离线可用（适合比赛 Demo）
- 纯 Python StateGraph（API 兼容 LangGraph），无需安装额外依赖

## 调用方式（后端）
```python
from carsoul_agent.agents.carsoul_agent import CarSoulGuardianAgent
agent = CarSoulGuardianAgent()
result = agent.handle(message="我的电池温度异常", user="alice")
print(result["answer"])
```

## 直接调用工作流
```python
from carsoul_agent.agents.core import CoreWorkflow, AgentState

state: AgentState = {
    "vehicle_state": {"brand": "Tesla", "model": "Model Y", "vehicle_id": 1},
    "driver_profile": {"driving_style": "eco"},
    "sensor_window": [{"battery_temp": 48, "soc": 75}],
    "trace_log": [],
}
result = CoreWorkflow.run(state)
print(result["explanation"])
print(f"Trace: {len(result['trace_log'])} entries")
```

## 测试
```bash
cd ai-agent
python -m pytest tests/test_agent.py -v
# 23 passed
```

## 后续演进（TASK009+）
- 接入 ChromaDB 长期向量记忆与 RAG 知识库（诊断 Agent 检索故障案例）
- 工具层对接真实数据库（替换模拟数据）
- 可选接入 LangGraph 替换纯 Python StateGraph（API 已兼容）
