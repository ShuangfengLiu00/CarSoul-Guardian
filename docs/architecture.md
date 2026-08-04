# CarSoul Guardian 技术架构总览（TASK008 完整版）

## 一、整体架构

CarSoul Guardian 采用 **前后端分离 + 独立 AI Agent 模块** 的架构，围绕"车辆数字生命档案"核心概念构建。

```
┌─────────────┐     HTTP/REST      ┌──────────────┐     Python import    ┌──────────────┐
│  Frontend   │  ───────────────▶  │   Backend    │  ──────────────────▶ │   AI Agent   │
│ React+Vite  │                    │   FastAPI    │                      │  模块(可独立) │
│ Ant Design  │                    │  SQLAlchemy  │                      │  6 Tools     │
└─────────────┘                    └──────────────┘                      └──────────────┘
                                        │                                      │
                                   Service Layer                           Prompt / Tool
                                   10 services                                / Memory
                                        │                                        │
                                   ┌────┴─────┐                                 │
                                   │Database  │ ◀───────────────────────────────┘
                                   │ 10 tables│
                                   └──────────┘
```

## 二、模块职责

| 模块 | 技术栈 | 职责 |
|------|--------|------|
| `frontend/` | React 18 + TS + Vite + TailwindCSS + Ant Design 5 | Dashboard、Agent 对话、车辆数字生命档案、用户中心 |
| `backend/` | Python 3.10+ + FastAPI + SQLAlchemy 2.0 + Pydantic v2 | API 网关、业务逻辑、安全鉴权、数据库访问、档案聚合 |
| `ai-agent/` | 独立 Python 包（预留 LangGraph） | Agent 管理、Prompt、6个车辆工具、记忆、工作流、知识库 |
| `database/` | PostgreSQL 16 / SQLite（开发回退）+ Redis 7 | 业务数据（10张表）+ 缓存 |

## 三、分层原则（不可违反）

1. **接口层不写业务逻辑**：`backend/app/api/*` 只做参数校验与调度。
2. **业务逻辑下沉到 services**：`backend/app/services/*` 负责编排，10个服务模块各司其职。
3. **AI 调用不写在接口里**：所有 LLM/Agent 调用经 `ai-agent` 模块封装，backend 通过统一适配层调用。
4. **可扩展多 Agent**：`ai-agent/agents` 每个文件一个 Agent，通过注册表管理。
5. **守护非控制**：Agent 仅给出建议与提醒，不替用户执行不可逆操作。

## 四、数据库 Schema（10 张表）

TASK007 实现了完整的车辆数字生命档案数据模型，以 `vehicles` 表为根实体，8 张子表通过 `vehicle_id` 外键关联。

```
users
  │
  └─ vehicles (根实体)
       ├── lifecycle_events        生命周期时间线
       ├── health_snapshots         健康快照
       │    └── health_items        健康明细项 (1:N)
       ├── maintenance_records      保养记录
       ├── maintenance_schedules    保养计划
       ├── driving_behaviors        驾驶行为
       ├── alerts                   告警
       ├── ownership_records        所有权记录
       └── digital_twins            数字孪生 (1:1)
```

### 4.1 表结构概览

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `users` | 用户 | id, username, email, hashed_password |
| `vehicles` | 车辆根实体 | id, owner_id, vin(唯一), brand, model, year, mileage, fuel_type, status, purchase_*, insurance_*, inspection_expiry |
| `lifecycle_events` | 生命周期事件 | vehicle_id, event_type, title, event_date, mileage, cost, severity |
| `health_snapshots` | 健康快照 | vehicle_id, health_score, 6个子系统分数, mileage, snapshot_time |
| `health_items` | 健康明细项 | snapshot_id, category, item_name, level, score, recommendation |
| `maintenance_records` | 保养记录 | vehicle_id, maintenance_type, title, maintenance_date, cost, parts(JSON) |
| `maintenance_schedules` | 保养计划 | vehicle_id, item_name, interval_km, interval_days, next_due_*, status, priority |
| `driving_behaviors` | 驾驶行为 | vehicle_id, record_date, trip_count, distance, safety_score, eco_score, harsh_*_count |
| `alerts` | 告警 | vehicle_id, level, title, status, triggered_at, recommendation |
| `ownership_records` | 所有权记录 | vehicle_id, owner_name, transfer_type, start_date, end_date, purchase_price |
| `digital_twins` | 数字孪生 | vehicle_id(唯一), model_version, sync_status, telemetry(JSON), config(JSON) |

### 4.2 设计要点

- **JSON 字段灵活扩展**：`maintenance_records.parts`、`digital_twins.telemetry/config` 使用 JSON 类型，适应不同车型差异。
- **自动状态计算**：保养计划的 `status` 字段在每次查询档案时动态重算（overdue/due/pending），无需手动维护。
- **软关联设计**：所有子表通过 `vehicle_id` 外键关联，删除车辆时级联清理。
- **时间索引**：`snapshot_time`、`record_date`、`event_date`、`triggered_at` 等时间字段建索引，加速范围查询。

## 五、Service 层架构（10 个服务）

业务逻辑完全下沉到 Service 层，API 路由仅做参数校验和调度。

| 服务 | 文件 | 职责 |
|------|------|------|
| `vehicle_service` | vehicle_service.py | 车辆 CRUD + **档案聚合**（核心） |
| `lifecycle_service` | lifecycle_service.py | 生命周期事件管理 |
| `health_service` | health_service.py | 健康快照 + 明细项管理 |
| `maintenance_service` | maintenance_service.py | 保养记录 + 计划管理 |
| `driving_behavior_service` | driving_behavior_service.py | 驾驶行为 + 汇总统计 |
| `alert_service` | alert_service.py | 告警管理（创建/确认/解决） |
| `ownership_service` | ownership_service.py | 所有权记录管理 |
| `digital_twin_service` | digital_twin_service.py | 数字孪生 + 遥测同步 |
| `user_service` | user_service.py | 用户注册/登录/JWT |
| `agent_service` | agent_service.py | Agent 调用适配层 |

### 5.1 档案聚合核心逻辑

`vehicle_service.get_archive()` 是系统的核心方法，一次查询聚合车辆的全部数字生命数据：

```
get_archive(vehicle_id)
  ├── 查询 vehicle 基本信息
  ├── 查询 lifecycle_events（按日期倒序）
  ├── 查询 health_snapshots（最近20条 + 明细项）
  ├── 查询 maintenance_records（按日期倒序）
  ├── 查询 maintenance_schedules → 动态重算 status
  ├── 查询 driving_behaviors（最近30天）
  ├── 查询 alerts（活跃优先）
  ├── 查询 ownership_records（按日期正序）
  ├── 查询 digital_twin
  └── 计算汇总：health_score, active_alert_count, total_cost, next_maintenance_items
```

## 六、API 路由结构

```
/api
├── /user                    用户认证
│   ├── POST /register
│   └── POST /login
├── /vehicle                 车辆数字生命档案
│   ├── GET /                列表
│   ├── POST /               创建
│   ├── GET /{id}            详情
│   ├── PUT /{id}            更新
│   ├── DELETE /{id}         删除
│   ├── GET /{id}/archive    ★ 完整档案聚合
│   ├── /{id}/lifecycle      生命周期 (GET/POST/DELETE)
│   ├── /{id}/health         健康快照 (GET/POST/DELETE + /latest)
│   ├── /{id}/maintenance    保养 (records + schedules)
│   ├── /{id}/driving-behavior  驾驶行为 (GET/POST/DELETE + /summary)
│   ├── /{id}/alerts         告警 (GET/POST/PATCH/DELETE)
│   ├── /{id}/ownership      所有权 (GET/POST/DELETE)
│   └── /{id}/digital-twin   数字孪生 (GET/POST/PATCH/DELETE + /telemetry)
├── /agent                   AI Agent
│   └── POST /chat
└── /health                  系统健康
    └── GET /overview
```

共 **38 个 RESTful 端点**，覆盖车辆数字生命档案的完整生命周期管理。

## 七、AI Agent 工具层

Agent 通过 9 个工具获取车辆数据并执行守护动作。读工具返回与种子数据一致的模拟数据（TASK009+ 对接真实数据库与 RAG），守护工具层是「守护非控制」红线的工程闸门。

### 7.1 读工具（6 个）

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `get_vehicle_info` | 车辆完整档案信息 | vin, vehicle_id |
| `get_health_score` | 健康指数 + 子系统分数 + 风险项 | vehicle_id |
| `get_maintenance_plan` | 保养计划（到期项 + 未来计划） | vehicle_id |
| `get_driving_behavior` | 驾驶行为分析（安全/能耗评分） | vehicle_id, days |
| `get_lifecycle_timeline` | 生命周期事件时间线 | vehicle_id |
| `get_alerts` | 活跃告警列表 + 处理建议 | vehicle_id |

### 7.2 守护工具（3 个，唯一可写工具）

| 工具名 | 功能 | 守护边界 |
|--------|------|----------|
| `push_reminder` | 向车主推送主动守护提醒 | 仅提醒，不控制 |
| `record_lifecycle_event` | 向数字生命档案追加事件记录 | 仅记录，不修改车辆状态 |
| `write_service_suggestion` | 持久化服务建议 | 仅写入建议文本 |

> **工具层闸门**：工具注册表中不存在任何控制执行器的工具（如 `brake_control`、`accelerate`、`steer`）。即使 LLM 幻觉也无法调用不存在的工具。所有守护动作记录在 `ActionStore` 中可供审计。

## 八、AI Agent 工作流（TASK008 AI 车辆医生 · 多智能体专家会诊）

### 8.1 架构总览

CarSoul Core Agent 用纯 Python StateGraph 实现（API 兼容 LangGraph，离线可用），共享状态 `AgentState` 在节点间流转，每个子 Agent 是一个节点函数。诊断节点升级为专家会诊中枢，召集五位专科专家并行会诊后汇总诊断。

```
START → perception(问诊) → {is_normal?}
                                │ no  → diagnosis(专家会诊) → risk(分级) → explainer(报告) → service(处方) → END
                                │ yes → explainer(巡检报告) → service → END
```

### 8.2 共享状态 AgentState

| 字段 | 产出节点 | 说明 |
|------|----------|------|
| `vehicle_state` | 输入 | 车辆数字孪生快照 |
| `driver_profile` | 输入 | 驾驶者画像（driving_style: eco/aggressive/balanced） |
| `sensor_window` | 输入 | 最近 N 个传感器读数 |
| `anomalies` | perception | 检出的异常列表 |
| `is_normal` | perception | 是否走正常报告分支 |
| `expert_opinions` | diagnosis | 五位专科专家的会诊意见（多智能体专家系统） |
| `diagnosis` | diagnosis | 会诊汇总后的根因结论（type/root_cause/severity/confidence） |
| `risk_assessment` | risk | 量化等级（level/probability/eta_hours/trend） |
| `explanation` | explainer | 用户语言解释（标注会诊来源） |
| `service_suggestion` | service | 建议与提醒 |
| `trace_log` | 全程 | 执行轨迹（推理可追溯） |

### 8.3 五子 Agent 职责（诊疗闭环）

| # | Agent | 诊疗角色 | 职责 | GOAI 闭环步骤 | Trace 标记 |
|---|-------|----------|------|---------------|------------|
| ① | perception | 问诊·体征采集 | 阈值检测 + 语义异常识别 | 感知 | `step=perceive` |
| ② | diagnosis | 专家会诊中枢 | 召集五专家并行会诊 + 汇总诊断 | 理解 + 推理 | `step=understand` / `step=reason` |
| ③ | risk | 风险分级 | 风险量化（等级/概率/ETA） | 推理量化 | `step=reason` |
| ④ | explainer | 诊断报告 | 按驾驶画像适配语言 | 调用工具 | `step=tool` |
| ⑤ | service | 处方·随访 | 推送提醒 + 记录生命周期 + 写入建议 | 执行任务 | `step=act` |

### 8.4 多智能体专家面板（五专科专家会诊）

诊断节点作为会诊中枢，召集五位专科专家并行诊断，每位专家只负责自己领域：

| 专家 | 专科 | 关注领域 | 核心能力 |
|------|------|----------|----------|
| PowertrainExpert | 动力系统 | 电池/发动机/电机 | 热失控征兆、电量损耗、过热检测 |
| ChassisExpert | 底盘系统 | 刹车/轮胎/悬挂 | 磨损极限、高里程老化、制动安全 |
| ElectricalExpert | 电气系统 | 传感器/电路/电子 | 故障码排查、传感器误报排除 |
| DrivingBehaviorExpert | 驾驶行为 | 习惯/安全评分 | 激烈驾驶风险、安全评分预警 |
| MaintenanceExpert | 保养规划 | 周期/成本/优先级 | 保养节点、健康衰退、优先级排序 |

每位专家输出结构化会诊意见（findings / severity / recommendation / confidence），由诊断中枢汇总成统一诊断结论。专家相互隔离，单个专家失败不影响其余会诊。

### 8.5 闭环保证

完整 GOAI 七环节闭环与五子 Agent 一一对应：

| GOAI 闭环环节 | CarSoul 实现 | 落点 Agent |
|---------------|-------------|------------|
| 感知 | 传感器窗口阈值 + 语义检测 | perception |
| 理解 | 专家会诊 + 故障案例知识库匹配 | diagnosis |
| 推理 | LLM 根因推理 + 风险量化 | diagnosis/risk |
| 调用工具 | 画像适配工具 | explainer |
| 执行任务 | 推送提醒 + 记录生命周期 | service |
| 反馈 | 用户收到提醒并可追问 | 前端交互 |
| 持续学习 | 建议采纳率回流（TASK010） | scoring 更新 |

### 8.6 离线降级策略

- 配置 `OPENAI_API_KEY` 时：感知做语义检测、专家做 LLM 根因增强、解释生成自然语言
- 未配置时：全部走规则引擎 + 专家知识库，阈值检测 + 模式匹配 + 模板生成，保证 Demo 可用
- LLM 调用失败时：各子 Agent 及专家内部 try/except 降级为规则响应

### 8.7 文件结构

```
ai-agent/carsoul_agent/agents/core/
├── __init__.py          # 包导出（含专家面板）
├── state.py             # AgentState + Trace 追踪（含 expert_opinions）
├── perception.py        # ① 问诊·体征采集 Agent
├── diagnosis.py         # ② 专家会诊中枢（召集专家 + 汇总诊断）
├── experts.py           # ★ 多智能体专家面板（五专科专家）
├── risk.py              # ③ 风险分级 Agent
├── explainer.py         # ④ 诊断报告 Agent
├── service.py           # ⑤ 处方·随访 Agent（守护工具层）
└── workflow.py          # StateGraph 状态图编排
```

## 九、前端架构

```
frontend/src/
├── pages/
│   ├── Dashboard.tsx          仪表盘总览
│   ├── VehicleArchive.tsx     ★ 车辆数字生命档案（核心页面）
│   └── AgentChat.tsx          Agent 对话
├── services/
│   ├── types.ts               全量 TypeScript 类型定义
│   ├── vehicleService.ts      28个车辆API方法
│   ├── agentService.ts        Agent API
│   ├── userService.ts         用户API
│   └── healthService.ts       健康API
├── layouts/MainLayout.tsx     侧边栏导航布局
├── stores/                    Zustand 状态管理
├── hooks/                     自定义 Hooks
└── utils/request.ts           Axios 封装 (GET/POST/PUT/PATCH/DELETE)
```

### VehicleArchive 页面结构

页面采用左右分栏 + 标签页布局：

- **左侧**：车辆列表（可切换选择）
- **右侧顶部**：4个摘要统计卡（健康分数、活跃告警、保养总费用、下次保养项）
- **右侧中部**：车辆基本信息卡（品牌/型号/VIN/里程/保险/年检等 16 项）
- **右侧底部**：7 个标签页
  1. 健康报告 — 仪表盘 + 子系统雷达 + 风险项列表
  2. 生命周期 — 时间线视图
  3. 保养记录 — 记录表 + 计划表
  4. 驾驶行为 — 汇总统计 + 每日数据表
  5. 告警 — 统计卡 + 告警列表（可确认/解决）
  6. 所有权 — 变更历史表
  7. 数字孪生 — 状态信息 + 遥测数据 + 配置

## 十、数据库连接策略

- 开发：SQLite（通过 `DATABASE_URL` 协议判断自动回退），零配置启动。
- 生产：PostgreSQL 16（Docker），通过 `DATABASE_URL=postgresql://...` 切换。
- Backend 通过 SQLAlchemy 2.0 `sessionmaker` 管理会话，依赖注入 `get_db()`。
- 启动时 `Base.metadata.create_all()` 自动建表，`seed_data.py` 插入演示数据。
- `psycopg[binary]` 驱动兼容 Python 3.10–3.14。

## 十一、扩展能力预留

- **多 Agent**：`ai-agent/agents/registry.py` 注册表 + 基类 `BaseAgent`。
- **知识库**：`ai-agent/memory/` 预留向量库目录（ChromaDB，TASK008+ 接入）。
- **多版本迭代**：API 统一前缀 `/api`，未来按 `/api/v2` 版本化。
- **用户系统**：JWT 鉴权预留，TASK009 完善角色权限与数据隔离。
- **实时遥测**：数字孪生 `telemetry` JSON 字段 + `/telemetry` 推送接口，为 IoT 实时数据预留。
- **多车型适配**：`fuel_type` 枚举覆盖燃油/混动/纯电，`battery_capacity`/`displacement` 按车型可选。
