# CarSoul OS V1.0 升级开发文档

> 版本：v1.1 · 2026-08-04（v1.0 · 2026-08-03 初版）
> 状态：已评审定稿（评委视角对位 + 代码库实证核查）
> 前置阅读：`goai-dasaijiedu/OS/CarOS.txt`（战略来源）、参赛手册（评审权重与红线）
> v1.1 变更：并入 4.3.2 赛题对位增量（见 §3A）——售后链路闭环、二手车购车顾问、赛题六段覆盖声明

---

## 0. 文档说明

本文档是 CarSoul Guardian → **CarSoul OS V1.0** 的完整升级开发方案。
制定原则：**不考虑赛程时间压力，按依赖关系做完整工程质量**；每一步结束系统都处于可演示状态。

核心定位切换：

```
旧：CarSoul Guardian —— 一个 AI 车辆医生应用
新：CarSoul OS V1.0 —— 面向智能汽车生命周期管理的开源 AI Agent 操作系统
```

一句话故事：**80% OS 内核 + 20% 冠军级 Demo，让评委相信看到的是未来汽车 AI 操作系统的 0.1 版本。**

---

## 1. 现状盘点（实证核查结论）

### 1.1 模块成熟度对位

| CarOS 目标模块 | 完成度 | 现状证据 | 差距本质 |
|---|---|---|---|
| agents/ 专家团队 | 85% | `ai-agent/carsoul_agent/agents/core/experts.py` + `extended_experts.py`，10 专家 ThreadPoolExecutor 真并行，单专家失败隔离 | 仅需按 battery/safety/value 语义重命名归位 |
| kernel/workflow_engine | 85% | `agents/core/workflow.py`（自研 StateGraph）+ `workflow_engine/engine.py`（DAG：Intent→Plan→Execute→Verify + Judge 仲裁） | 基本就绪 |
| kernel/governance | 80% | `governance/` 9 文件：权限/沙箱/版本/裁判 + MCP Registry（15 个车辆能力接口） | 超前于方案，需对外文档化 |
| kernel/agent_runtime | 60% | `agents/registry.py` + 基类 + 三级路由（问候/知识/车辆） | 未 SDK 化：无 `create_agent()/register_skill()` 开发者 API |
| digital_twin/ | 55% | 9 张数字生命表 + `api/digital_twin` 19 端点 + `data_generator.refresh_digital_state` | 部件模型是 JSON blob，非结构化组件模型 |
| knowledge/ | 45% | ChromaDB/内存双后端 + BM25 混合检索 + Hash 嵌入降级，9 篇文档 | 无成规模 repair_cases / failure_patterns |
| skills/ | 40% | skill 治理端点 + `skill_memory.py` | 专家不是可插拔技能，无注册协议 |
| kernel/memory_engine | 30% | `memory/` 4 个类（conversation/episodic/skill/evolution） | **全部纯内存，重启即丢**；无"事件→影响"车辆记忆模型 |
| 杀手 Demo | 25% | `StoryMode.tsx` 五幕剧场（单场景剧本） | 缺多年时间线叙事 + 衰减预测 + 估值输出 |
| vehicle_protocol/ | 15% | `data_generator.py` 数据播种器 + MCP Registry | 无独立 Vehicle Schema 标准、无车型化模拟器产品 |
| 开源三件套 | 5% | MIT LICENSE + README | 0/3：SDK、Schema、Simulator 均未立 |

### 1.2 必须先修复的存量缺陷

| 缺陷 | 位置 | 严重度 |
|---|---|---|
| 后端无法启动：`TaskCompletedRequest` 在 368 行被使用、387 行才定义 | `backend/app/api/governance/router.py` | 🔴 致命（正中"无法复现 Demo 取消评奖资格"红线） |
| 后端 30 个测试全部收集失败（同一导入错误导致） | `backend/tests/` | 🔴 高 |
| 过时断言：断言 5 专家、实际已 10 专家 | `ai-agent/tests/test_agent.py::test_diagnosis_includes_expert_opinions` | 🟡 中 |
| README 任务状态过时（TASK009-011 标 ⏳，实际已完成） | `README.md` vs `docs/roadmap.md` | 🟡 中 |
| ActionStore 审计账本纯内存 | `tools/guard_tools.py` | 🟡 中（可追溯性考点） |

---

## 2. 目标架构

### 2.1 目录结构（目标形态）

```
carsoul-os/
├── kernel/                     # OS 内核
│   ├── agent_runtime/          # Agent 运行时（注册/路由/生命周期）
│   ├── workflow_engine/        # 工作流引擎（StateGraph + DAG）
│   ├── memory_engine/          # ★ 记忆引擎（车辆长期记忆，持久化）
│   └── governance/             # 治理（权限/沙箱/版本/裁判/MCP Registry）
│
├── digital_twin/               # 数字孪生
│   ├── vehicle_model/          # 整车模型
│   ├── component_model/        # ★ 部件级模型（Battery/Motor/Chassis 状态机）
│   └── lifecycle/              # 生命周期
│
├── vehicle_protocol/           # ★ 车辆协议层
│   ├── vehicle_schema/         # ★ 数据标准（Pydantic 模型 + JSON Schema + semver）
│   ├── mcp_adapter/            # MCP 适配（基于现有 MCP Registry）
│   └── simulator/              # ★ 虚拟车模拟器（3 车型画像 + 时间压缩）
│
├── skills/                     # ★ 技能层（可插拔）
│   ├── battery_skill/
│   ├── maintenance_skill/
│   ├── safety_skill/
│   └── valuation_skill/
│
├── agents/                     # Agent 团队（= 技能的编排组合）
│   ├── guardian_agent/
│   ├── battery_agent/
│   ├── diagnosis_agent/
│   ├── safety_agent/
│   └── value_agent/
│
├── knowledge/                  # 知识库
│   ├── repair_cases/           # ★ 维修案例（50-100 条结构化）
│   ├── automotive_docs/        # 汽车文档（现有 9 篇迁入）
│   └── failure_patterns/       # ★ 故障模式库（兼任评测集）
│
├── apps/                       # 演示应用壳（现有 frontend/backend 迁入）
│   ├── web/                    # React 前端
│   └── server/                 # FastAPI 后端
│
├── demo/                       # 冠军 Demo
│   ├── virtual_vehicle/        # 虚拟车演示
│   ├── dashboard/              # 仪表盘
│   └── health_report/          # ★ 「一辆车的一生」时间线报告
│
└── docs/                       # 文档（quickstart/architecture/API/schema spec/合规）
```

### 2.2 数据流（升级后）

```
Simulator ──TelemetryFrame──▶ Digital Twin ──快照──▶ Agent Runtime
（时间压缩，符合Schema）     （组件状态机）            │
                                                      ▼
Memory Engine ◀──写入 impact── Skills 编排执行 ──▶ 健康报告/提醒
（event→impact 链）                │
                                   ▼
                            Knowledge（案例/故障模式增强）
```

---

## 3. 开发路线（10 步，严格依赖序）

### 第 0 步：止血基线（一切的前提）

**改动：**
1. 修复 `backend/app/api/governance/router.py`：将 `TaskCompletedRequest` 类定义移到使用之前（或顶部统一定义）。
2. 跑通 `ai-agent/tests`（36 个）+ `backend/tests`（30 个）全绿；修正 5→10 专家过时断言。
3. 挂 CI（GitHub Actions 或等价）：push 即跑两套测试。
4. 同步 README 任务状态至与 `docs/roadmap.md` 一致。

**验收（DoD）：** 干净环境 `uvicorn app.main:app` 启动成功；两套测试 0 失败；CI 红灯/绿灯可观测。

---

### 第 1 步：Vehicle Schema（OS 的"宪法"）

全局契约，必须先立。从现有 24 张表提炼公开数据标准，独立于 ORM。

**交付物：**
- `vehicle_protocol/vehicle_schema/` 独立包（`carsoul-schema`），含 Pydantic v2 模型 + 导出的 JSON Schema + semver 版本号：

```python
VehicleIdentity(vin, brand, model, year, fuel_type, battery_capacity?)
BatteryState(soh: float, temperature: float, charge_cycles: int, fast_charge_ratio: float)
MotorState(efficiency: float, wear: float)
ChassisState(brake_wear: float, tire_wear: float, suspension_health: float)
DrivingProfile(style: Literal["eco","balanced","aggressive"], safety_score: float, eco_score: float)
LifecycleEvent(event_type: str, date: date, mileage: float, impact: ImpactRef?)
TelemetryFrame(ts: datetime, battery: BatteryState, motor: MotorState,
               chassis: ChassisState, driving: DrivingProfile)   # 模拟器发射单元
```

- `docs/schema-spec.md`：字段含义、单位、取值范围、模拟逻辑与适用边界（合规文档复用）。

**验收：** schema 独立成包可 `pip install -e`；第三方只看 spec 文档能构造合法数据并通过校验。

---

### 第 2 步：虚拟车模拟器（OS 的"发电厂"）

将 `backend/app/services/data_generator.py`（现有 generate_sensor_data/generate_trips/generate_faults/run_simulation）升级为独立产品。

**改动：**
- 新建 `vehicle_protocol/simulator/`：
  - `VehicleProfile`：车型画像（衰减曲线、传感器蓝图、行为模型）；
  - 内置 3 画像：`performance_ev`（高性能纯电）、`family_ev`（家用纯电）、`hybrid`（混动）；
  - **时间压缩引擎**：`run(days=365)` 秒级产出全年 TelemetryFrame 流；
  - **剧本编排**：充电习惯（快充比例）、季节温度、路况配比、异常注入（冷却系统故障等）。
- API：`create_virtual_vehicle(profile: str, seed: int) -> VirtualVehicle`；数据经后端 ingestion 落库（复用现有端点）。

**验收：** `create_virtual_vehicle("family_ev").run(days=365)` 产出 365 天合规遥测；同一 seed 结果可复现；异常剧本可触发下游告警。

---

### 第 3 步：数字孪生组件化

**改动：**
- 新建 `digital_twin/component_model/`：`BatteryTwin / MotorTwin / ChassisTwin`，各自状态机（normal → degrading → warning → critical），字段全面对齐 Schema。
- `digital_twins.telemetry` JSON blob 迁移为经 Schema 校验的结构化数据（保留 JSON 存储，加校验层）。
- soul-score 改为从部件健康推导（可解释：每个扣分项可追溯到部件）。

**验收：** 模拟器数据流 → 孪生体实时同步；soul-score 变化可解释到具体部件状态变迁。

---

### 第 4 步：记忆引擎（核心创新，投入最厚）

OS 故事的心脏，AI+汽车赛题"用车生命周期理解"考点的实体化。

**改动：**
- 新建 `kernel/memory_engine/`，持久化（SQLite/PostgreSQL）：

```sql
vehicle_memories(
  id, vehicle_id, occurred_at, event_type,       -- 发生了什么
  payload JSON,                                   -- 事件细节（如快充次数、温度曲线）
  impact_target, impact_delta, confidence,        -- 影响了什么、影响多大（如 battery_stress +0.3）
  source,                                         -- 来源（simulator / diagnosis / user）
  created_at
)
```

- 记忆 API：`remember(event)` / `recall(vehicle_id, topic=None, since=None)` / `summarize_for_agent(vehicle_id)`（产出注入 prompt 的记忆摘要）。
- 集成点：service Agent 写记忆；perception/diagnosis 读记忆；`lifecycle_events` 保留为原始日志，**memory = 带影响语义的解释层**。
- 现有 `memory/` 4 个内存类迁入并改造为引擎的会话/情景缓存层。

**验收：** 重启后记忆仍在；会诊意见能引用具体历史记忆条目（"您 2026 年 8 月快充频次上升 40%，与当前电池温升相关"）；`summarize_for_agent` 输出可控长度（token 预算内）。

---

### 第 5 步：Runtime SDK（OS 的"门面"）

在现有 registry + workflow_engine + governance 之上封装开发者 API。放在记忆引擎之后，让 SDK 原生带记忆钩子。

**交付物：** `carsoul-runtime` 包，公开 API：

```python
from carsoul_os import create_agent, register_skill, execute_workflow

agent = create_agent(name="my_guardian",
                     skills=[BatterySkill(), SafetySkill()],
                     memory="sqlite:///carsoul.db",
                     governance=GovernanceProfile(read_only=True))
result = execute_workflow(agent, vehicle_frame, user_query="电池最近怎么样")
```

**验收：** 外部脚本 ≤20 行跑起一个自定义汽车 Agent；治理约束经 SDK 默认生效（只读工具白名单）。

---

### 第 6 步：专家 Skills 化

**改动：**
- 定义技能协议：

```python
class Skill(Protocol):
    name: str; domain: str
    def match(self, state: AgentState) -> bool: ...
    def run(self, state, tools, memory, knowledge) -> SkillFinding: ...
```

- 现有 10 个专家（`experts.py` + `extended_experts.py`）逐个改造为 Skill 实现，迁入 `skills/`；
- `agents/` 下的 Agent = 技能的编排组合（guardian = 全量技能 + 汇总；battery_agent = battery + safety 子集）。

**验收：** 新增一个自定义 Skill 不改框架代码即可注册生效；10 个技能全部经 `register_skill` 装载；既有 36 个 Agent 测试保持绿色（断言同步更新）。

---

### 第 7 步：知识库扩容

**改动：**
- `knowledge/repair_cases/` + `failure_patterns/`：扩充至 50–100 条结构化条目：

```yaml
- id: BP-001
  symptom: 充电速度下降20% + 电池温度波动
  system: battery
  root_cause: 电芯衰减早期 / 冷却效率下降
  recommended_action: 降低快充比例 + 冷却系统检查
  confidence: 0.8
```

- 现有 9 篇文档迁入 `automotive_docs/`；检索层不变（ChromaDB/内存 + BM25 混合）。

**验收：** 知识条数 ≥50；该库同时作为第 9 步评测集的事实标准（ground truth）。

---

### 第 8 步：杀手 Demo「一辆车的一生」

前面所有件的合力，20% 的展示层，100% 的决胜点。

**改动：**
- 后端：新增时间线模拟端点（调用模拟器时间压缩 + 记忆引擎回放 + Agent 团队触发）+ 健康报告生成（评分 / 12 个月衰减预测 / 二手估值区间）。
- 前端：新增 `/timeline` 页面：
  - 年份滑块 2025（出生，Battery 100%）→ 2026（用车：快充↑、高速↑、冬季）→ 2027（异常：充电速度 -20%、温度波动）；
  - 记忆流侧栏（记忆引擎逐年条目可见）；
  - 异常触发后展示 Agent 协作视图（guardian 召集 battery/diagnosis/safety/value 并行）；
  - 终幕报告卡：健康评分 87 · 12 个月后电池衰减 +4% · 建议调整充电策略 · 二手估值预计提升 1.8 万元。
- 演示页保留"演示模式·模拟数据"角标（红线 2 合规）。

**验收：** 3 分钟讲完一辆车的一生；报告每个数字可点击追溯到记忆条目/遥测/会诊意见。

---

### 第 9 步：开源三件套 + 评测 + 文档

**交付物：**
1. **carsoul-runtime**（SDK 文档 + quickstart + 示例）；
2. **carsoul-schema**（规范文档 + 校验器）；
3. **carsoul-simulator**（3 车型画像 + 剧本示例）；
4. **评测报告**：以 failure_patterns 为 ground truth，跑 50–100 例，输出诊断准确率 / 专家召回率 / 闭环完成率 / 幻觉防护（无控制类工具调用）指标；
5. **文档集**：架构图、API 参考、合规说明（数据来源/模拟逻辑/脱敏/不替代专业判断声明）、第三方依赖披露（开源依赖 + 商业 API + 闭源模型使用范围）；
6. ActionStore 审计账本持久化（SQLite 落表），补齐可追溯短板；
7. 仓库按 §2.1 重组，README 重写为 OS 叙事。

**验收：** 干净机器按 README 从零复现核心 Demo（照抄手册附录 C 清单逐项打勾）；评测报告可复跑。

---

## 3A. 赛题对位增量（v1.1，源自 4.3.2 AI+汽车对位检查）

对位结论：生命周期六段（购车/用车/养车/售后/出行/座舱）当前覆盖 2 深 + 1 半 + 3 缺。手册允许细分场景（"不限制创意边界"），故不追求六段全做，采取"**补两段、声明两段、收敛口径**"策略。

### 3A.1 售后链路闭环（插入第 6 步执行，成本最低、对分最准）

AI+汽车个性化评审点"服务链路适配"的直接证据。复用现有 `create_service_order` 守护工具与 escalation 三级升级：

- 服务单状态机：`created → booked → in_service → done → closed`（落库，非内存）；
- 进度查询端点：`GET /api/vehicle/{id}/service-orders` + 单详情；
- 反馈包装：risk feedback（confirmed/false_alarm/no_event/partial）对外呈现为"售后反馈整理"入口；
- 前端：售后工单列表 + 进度时间线（挂入 VehicleArchive 新标签页）。

**验收：** 从"Agent 诊断 → 创建工单 → 进度推进 → 完成 → 用户反馈"全链路可在 UI 走通；工单全量落库可追溯。

### 3A.2 二手车购车顾问（新增步骤，插在第 6 步之后、第 7 步之前）

补齐"购车"段，复用现有资产，不重写：`value_agent`（估值）+ 数字孪生 + Vehicle Passport 叙事，从"帮车主守护"延伸为"帮买家验车"。

- 新技能 `purchase_advisor_skill`：输入二手车 VIN/档案 → 输出验车报告（健康分解读、事故/维修史摘要、残值区间、议价建议）；
- 与 valuation_skill 共用估值模型；报告标注"辅助参考，不替代专业检测"（边界声明）；
- 演示路径：同一辆虚拟车，车主视角（守护）与买家视角（验车）双角色切换——叙事增量极大。

**验收：** 买家视角可独立完成一次验车闭环；报告每个结论可追溯到孪生数据与记忆条目。

### 3A.3 赛题六段覆盖声明（并入第 9 步文档集）

诚实声明代替虚假全覆盖，安全排除反而加分：

- 文档《赛题对位说明》：六段覆盖表（用车/养车=深覆盖，售后/购车=本次补齐，出行/座舱=V2 路线图）；
- **座舱主动排除理由成文**："座舱内实时交互邻近'驾驶中高风险操作'边界，V1.0 主动不做，是对车辆安全边界的自觉"——直接回应边界要求；
- 出行段 V2 定位：续航/充电规划（battery_twin 自然延伸），不承诺路线/天气（需地图 API）；
- 全项目口径收敛：对外叙事从"全生命周期"调整为"**用车·养车·售后·购车的健康管理纵深 + 出行/座舱路线图**"，消除 claim 大于覆盖的答辩风险。

**验收：** PPT、README、合规文档三处口径一致；评委拿 4.3.2 对表时每一段都有交代。

---

## 4. 迁移映射表（旧 → 新）

| 现有资产 | 去向 |
|---|---|
| `ai-agent/carsoul_agent/agents/registry.py + base.py` | `kernel/agent_runtime/` |
| `agents/core/workflow.py + workflow_engine/` | `kernel/workflow_engine/` |
| `governance/`（9 文件） | `kernel/governance/` |
| `memory/`（4 类） | `kernel/memory_engine/`（缓存层） |
| `experts.py + extended_experts.py` | `skills/`（10 个技能实现） |
| `agents/core/`（perception/diagnosis/risk/explainer/service/escalation） | `agents/guardian_agent/` 编排逻辑 |
| `knowledge/`（RAG + 9 文档） | `knowledge/automotive_docs/` |
| `backend/app/services/data_generator.py` | `vehicle_protocol/simulator/` 地基 |
| MCP Registry（15 接口） | `vehicle_protocol/mcp_adapter/` |
| `backend/` + `frontend/` | `apps/server` + `apps/web` |
| `StoryMode.tsx` 五幕剧场 | `demo/`（保留为备用演示，标注演示模式） |

---

## 5. Scope 守卫（即使不限时也不做）

1. **不做真实车辆接入** —— Demo 阶段模拟器就是正确答案，且避开安全红线；
2. **不碰任何控制类能力** —— 守住"守护非控制"，工具层永无 brake/steer/accelerate；
3. **不推倒前端重写** —— 22 个页面保留，新增 `/timeline` 一页；
4. **不追逐"所有汽车能力"** —— V1.0 冻结在本文档 10 步范围内；
5. **不引入 LangGraph 等重型框架** —— 自研 StateGraph 已是差异化卖点，保持零依赖可运行。

---

## 6. 红线合规清单（对照参赛手册第 11 章）

| 红线 | 本项目对策 | 落实步骤 |
|---|---|---|
| 按 README 无法复现 Demo → 取消评奖资格 | CI 保底 + 干净机器从零复现验收 | 第 0、9 步 |
| 虚假演示/结果造假 → 取消成绩 | 演示模式角标 + 主演示走真实调用链；模拟数据说明模拟逻辑与边界 | 第 8 步 + schema-spec |
| 路演材料与 Demo 一致 | PPT 每个能力点必须有可运行对应物 | 第 8、9 步 |
| 第三方依赖/商业 API/闭源模型披露 | 依赖披露文档（OpenAI 使用范围 + 离线降级方案） | 第 9 步 |
| 不影响车辆安全控制、不替代专业判断 | 工具层闸门 + 合规声明 + 报告页人工确认提示 | 全程 |

---

## 7. 风险与对策

| 风险 | 等级 | 对策 |
|---|---|---|
| 目录重组破坏现有导入，回归失控 | 高 | 第 0 步 CI 先行；重组单独一个 PR，纯移动不改逻辑，测试绿才合入 |
| 记忆引擎范围蔓延（做成通用记忆框架） | 中 | 冻结为"车辆 event→impact"单一场景；通用化留到 V2 |
| 估值功能被质疑数据来源 | 中 | 估值输出为区间 + 方法论说明（基于健康分/里程/车龄的可解释模型），不声称接真实二手车行情 |
| 无 LLM Key 时演示智能感不足 | 中 | 离线规则路径专门打磨（阈值表 + 故障模式库 + 模板），演示脚本避开弱区 |
| SDK 封装暴露内部不一致 | 低 | 第 5 步先写 API 契约测试，再实现 |

---

## 8. 完成定义（V1.0 总验收）

- [ ] 两套测试全绿 + CI 可观测
- [ ] `pip install carsoul-runtime carsoul-schema carsoul-simulator` 三包独立可用
- [ ] 外部开发者 20 行代码创建自定义汽车 Agent（SDK 验收脚本）
- [ ] 「一辆车的一生」3 分钟演示：时间轴 + 记忆流 + 会诊 + 可追溯报告
- [ ] 评测报告：≥50 例，四项指标可复跑
- [ ] 干净机器按 README 从零复现成功
- [ ] 合规三件套：数据来源说明 / 依赖披露 / 不替代专业判断声明
- [ ] 售后工单全链路可走通（诊断→工单→进度→完成→反馈），全量落库
- [ ] 二手车验车闭环独立可演示（买家视角），结论可追溯
- [ ] 《赛题对位说明》发布：六段覆盖表 + 座舱安全排除理由 + 出行 V2 定位，三处口径一致
