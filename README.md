# CarSoul OS V1.0

> 面向智能汽车生命周期管理的开源 AI Agent 操作系统

**80% OS 内核 + 20% 冠军级 Demo — 让你看到的是未来汽车 AI 操作系统的 0.1 版本。**

CarSoul OS 不是传统汽车工具，也不是聊天机器人。它是一套面向智能汽车全生命周期的 AI Agent 操作系统：以车辆数字孪生为感知层、记忆引擎为长期状态、可插拔技能为专家能力、治理层为安全闸门，构建「感知 → 诊断 → 记忆 → 技能匹配 → 技能执行 → 治理审计 → 生成报告」的完整闭环。

---

## 一、三条不可违反的红线

1. **不是聊天机器人** — 每次回答都落到具体车辆状态 / 数据 / 建议
2. **必须闭环** — 分析 → 建议 → 行动指引 → 后续追踪
3. **守护非控制** — 只给建议与提醒，绝不替用户执行不可逆操作

---

## 二、OS 架构

```
carsoul-os/
├── kernel/                     # OS 内核
│   ├── runtime/                # Agent 运行时（create_agent / execute_workflow / 治理）
│   │   ├── skills/             # 10 个专家技能 + 5 个 Agent 预设
│   │   ├── governance.py       # 治理（只读白名单 + 禁止控制类工具）
│   │   └── workflow.py         # 7 阶段工作流管道
│   └── memory_engine/          # 记忆引擎（SQLite 持久化 · event→impact 链）
│
├── digital_twin/               # 数字孪生
│   └── component_model/        # 部件级模型（Battery / Motor / Chassis 状态机）
│
├── vehicle_protocol/           # 车辆协议层（开源三件套之二）
│   ├── vehicle_schema/         # 数据标准（Pydantic v2 + JSON Schema + semver）
│   └── simulator/              # 虚拟车模拟器（3 车型画像 + 时间压缩 + 异常注入）
│
├── ai-agent/                   # AI Agent 包（carsoul_agent）
│   ├── knowledge/              # 知识库（62 YAML 条目 + 9 篇汽车文档）
│   │   ├── failure_patterns/   # 故障模式库（29 条，兼任评测集）
│   │   └── repair_cases/       # 维修案例库（33 条）
│   └── tools/                  # 工具层（ActionStore SQLite 审计账本）
│
├── backend/                    # 演示应用后端（FastAPI）
├── frontend/                   # 演示应用前端（React 18 + Ant Design 5）
└── docs/                       # 架构 / API / 合规 / 评测报告
```

### 数据流

```
Simulator ──TelemetryFrame──▶ Digital Twin ──快照──▶ Agent Runtime
（时间压缩，符合Schema）       （组件状态机）           │
                                                       ▼
Memory Engine ◀──写入 impact── Skills 编排执行 ──▶ 健康报告 / 提醒
（event→impact 链）                │
                                   ▼
                            Knowledge（案例 / 故障模式增强）
```

---

## 三、开源三件套

三个独立 Python 包，可单独安装使用：

| 包名 | 目录 | 说明 |
|------|------|------|
| **carsoul-schema** | `vehicle_protocol/vehicle_schema/` | 车辆数据标准（Pydantic v2 模型 + JSON Schema + semver 版本管理） |
| **carsoul-simulator** | `vehicle_protocol/simulator/` | 虚拟车模拟器（3 车型画像 + 时间压缩 + 异常注入 + 可复现种子） |
| **carsoul-runtime** | `kernel/` | Agent 运行时 SDK（create_agent / execute_workflow / 治理 / 记忆引擎 / 10 技能） |

### 安装

```bash
pip install -e vehicle_protocol/    # carsoul-schema + carsoul-simulator
pip install -e kernel/              # carsoul-runtime
```

### SDK Quick Start（≤20 行）

```python
from carsoul_os import (
    create_agent, execute_workflow,
    GovernanceProfile, register_all_expert_skills,
)
from vehicle_protocol.simulator import create_virtual_vehicle

# 1. 创建虚拟车并生成遥测数据
vehicle = create_virtual_vehicle("family_ev", seed=42)
frames = vehicle.run(days=30)

# 2. 创建守护 Agent（默认只读治理）
agent = create_agent(
    name="my_guardian",
    memory="sqlite:///carsoul.db",
    governance=GovernanceProfile(read_only=True),
)
register_all_expert_skills()

# 3. 执行诊断工作流
result = execute_workflow(agent, frames, "电池最近怎么样")
print(result.answer)
```

### 内置专家技能

| 技能 | 领域 | 说明 |
|------|------|------|
| powertrain_skill | 动力系统 | 电池 / 电机 / 发动机诊断 |
| chassis_skill | 底盘系统 | 刹车 / 轮胎 / 悬挂 |
| electrical_skill | 电气系统 | 传感器 / 电路 |
| driving_behavior_skill | 驾驶行为 | 驾驶习惯分析 |
| maintenance_skill | 保养规划 | 保养周期 / 成本 |
| vehicle_value_skill | 车辆价值 | 折旧 / 保值率 |
| environment_skill | 环境适应 | 温度 / 天气 / 路况 |
| charging_skill | 充电智能 | SOC / 充电策略 |
| energy_optimization_skill | 能耗优化 | 驾驶风格 / 能效 |
| user_companion_skill | 用户陪伴 | 个性化建议 |

### Agent 预设

5 个预设技能组合：`guardian`（全量 10 技能）、`battery_agent`、`safety_agent`、`value_agent`、`energy_agent`。

更多 API 细节见 `kernel/README.md`。

---

## 四、本地启动

### 前置

- Python 3.10+
- Node.js 20+

### 方式 A：一键启动（推荐）

```bash
cp .env.example .env
# Windows
.\deploy\start-dev.ps1
# Linux/macOS
bash deploy/start-dev.sh
```

启动后：
- 前端：http://localhost:5173
- 后端：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 方式 B：手动分步

```bash
# 后端
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  # source .venv/bin/activate (mac/linux)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端（新终端）
cd frontend
npm install
npm run dev
```

### 方式 C：Docker 全栈

```bash
cp .env.example .env
docker compose up --build
```

> **离线可用：** 即使没有 PostgreSQL 和 LLM Key，后端仍可启动（SQLite 回退），Agent 走规则响应，适合比赛 Demo。

### 「一辆车的一生」Demo

启动后端后访问 `/api/timeline/demo`，或在前端侧边栏点击「一辆车的一生」进入时间轴演示页面。演示包含：
- 年份滑块（2025 出生 → 2026 使用 → 2027 异常）
- 遥测面板（电池 / 电机 / 底盘实时数据）
- 生命事件时间线
- 记忆流侧边栏
- Agent 协作诊断视图
- 可追溯终检报告卡

> ⚠️ 演示页面标注红色「演示模式 · 模拟数据」角标，后端 `demo_mode` 始终为 `True`，返回确定性结果。

---

## 五、评测报告

以 `failure_patterns`（29 条）和 `repair_cases`（33 条）共 62 条 YAML 条目作为 ground truth，运行 Agent 工作流评测：

| 指标 | 通过数 | 总数 | 通过率 |
|------|--------|------|--------|
| 诊断准确率 (Diagnostic Accuracy) | 53 | 62 | **85.5%** |
| 专家召回率 (Expert Recall) | 62 | 62 | **100.0%** |
| 闭环完成率 (Closed-loop Completion) | 62 | 62 | **100.0%** |
| 幻觉防护 (Hallucination Protection) | 62 | 62 | **100.0%** |

复跑评测：

```bash
python kernel/tests/run_evaluation.py
```

完整报告见 `docs/evaluation-report.md`。

---

## 六、合规文档

| 文档 | 说明 |
|------|------|
| `docs/compliance.md` | 数据来源 / 模拟逻辑 / 脱敏 / 不替代专业判断声明 |
| `docs/dependency-disclosure.md` | 第三方依赖披露（开源依赖 + 商业 API + 闭源模型使用范围） |
| `docs/schema-spec.md` | Vehicle Schema 规范（数据标准 + semver 版本规则） |
| `docs/architecture.md` | 系统架构图与分层设计 |

---

## 七、技术栈

| 层 | 技术 |
|------|------|
| OS 内核 | Python 3.10+ · Pydantic v2 · SQLite |
| 数字孪生 | 自研组件状态机（Battery / Motor / Chassis Twin） |
| 前端 | React 18 · TypeScript · Vite · TailwindCSS · Ant Design 5 · Zustand · Recharts |
| 后端 | Python 3.11 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · JWT |
| 数据库 | PostgreSQL 16 · Redis 7（开发可回退 SQLite） |
| CI | GitHub Actions（Python 3.10/3.11 矩阵 + Node 20 前端构建） |

---

## 八、环境配置

参考 `.env.example`，关键字段：

| 变量 | 说明 | 默认 |
|------|------|------|
| `ENVIRONMENT` | development / production | development |
| `DATABASE_URL` | PostgreSQL 连接串（开发可留空回退 SQLite） | sqlite |
| `JWT_SECRET` | JWT 签名密钥（生产务必修改） | change-me |
| `OPENAI_API_KEY` | LLM 密钥（留空则 Agent 走离线规则响应） | 空 |
| `MODEL_NAME` | 模型名 | gpt-4o-mini |
| `CORS_ORIGINS` | 允许的前端来源 | localhost:5173 |

---

## 九、开发路线

详见 `docs/roadmap.md` 和 `docs/carsoul-os-v1.0-dev-plan.md`。

### TASK 任务列表

| TASK | 名称 | 状态 |
|------|------|------|
| TASK001-011 | 产品定位 → Demo 场景包装 | ✅ 全部完成 |
| Step 1 | Vehicle Schema（OS 的「宪法」） | ✅ |
| Step 2 | Virtual Vehicle Simulator | ✅ |
| Step 3 | Digital Twin Componentization | ✅ |
| Step 4 | Memory Engine | ✅ |
| Step 5 | Runtime SDK | ✅ |
| Step 6 | Expert Skills Integration | ✅ |
| Step 7 | Knowledge Base Expansion | ✅ |
| Step 8 | 「一辆车的一生」Demo | ✅ |
| Step 9 | 开源三件套 + 评测 + 文档 | ✅ |

---

## 十、基础 API

| Method | Path | 说明 |
|--------|------|------|
| GET | `/` | 项目信息 |
| GET | `/health` | 健康探针 |
| POST | `/api/user/register` | 用户注册 |
| POST | `/api/user/login` | 用户登录 |
| GET | `/api/vehicle` | 车辆列表 |
| POST | `/api/vehicle` | 添加车辆 |
| POST | `/api/agent/chat` | Agent 对话 |
| GET | `/api/health/overview` | Dashboard 概览数据 |
| GET | `/api/timeline/demo` | 「一辆车的一生」演示数据 |

完整契约见 `docs/api-contract.md`。

---

## 十一、测试

```bash
# Schema + Simulator 测试
cd vehicle_protocol && python -m pytest tests/ -v

# 数字孪生测试
cd digital_twin && PYTHONPATH=..:../vehicle_protocol python -m pytest tests/ -v

# 内核测试（记忆引擎 + Runtime SDK + 技能）
cd kernel && PYTHONPATH=..:../vehicle_protocol:../digital_twin:../ai-agent python -m pytest tests/ -v

# AI Agent 测试（含知识库扩展 + ActionStore 持久化）
cd ai-agent && python -m pytest tests/ -v

# 后端测试（含 Timeline Demo）
cd backend && DATABASE_URL="sqlite:///./test_carsoul.db" python -m pytest tests/ -v

# 前端类型检查 + 构建
cd frontend && npx tsc --noEmit && npm run build

# 评测脚本
python kernel/tests/run_evaluation.py
```

---

## License

MIT
