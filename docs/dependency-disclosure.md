# CarSoul Guardian 第三方依赖披露文档

> 版本：v2.0 · 最后更新：2026-08-04
> 适用范围：CarSoul Guardian 全部模块（backend / ai-agent / vehicle_protocol / frontend）
> 数据来源：`backend/requirements.txt`、`ai-agent/requirements.txt`、`vehicle_protocol/pyproject.toml`、`frontend/package.json`
> 变更摘要（v2.0）：新增 OpenAI 费用假设与成本测算、本地模型替代方案（Ollama/Qwen）、锁定风险分析、完整 License 清单、售后闭环新增依赖说明

---

## 一、开源依赖

### 1.1 后端（backend/requirements.txt）

| 依赖 | 版本要求 | 类型 | 用途 |
|------|----------|------|------|
| FastAPI | >=0.111 | 运行时 | Web 框架，提供 RESTful API 网关 |
| Uvicorn[standard] | >=0.30 | 运行时 | ASGI 服务器，运行 FastAPI 应用 |
| python-multipart | >=0.0.9 | 运行时 | multipart 表单解析 |
| Pydantic | >=2.9 | 运行时 | 数据验证与序列化（Schema 定义） |
| pydantic-settings | >=2.5 | 运行时 | 配置管理与环境变量加载 |
| python-dotenv | >=1.0 | 运行时 | `.env` 文件加载 |
| SQLAlchemy | >=2.0.30 | 运行时 | ORM，数据库访问层（11 张表，含售后工单表） |
| psycopg[binary] | >=3.2 | 运行时（可选） | PostgreSQL 驱动（psycopg3），仅生产环境使用；开发环境 SQLite 无需安装 |
| passlib[bcrypt] | >=1.7.4 | 运行时 | 密码哈希（bcrypt 算法） |
| python-jose[cryptography] | >=3.3.0 | 运行时 | JWT 令牌生成与验证（HS256 签名） |
| email-validator | >=2.0 | 运行时 | 邮箱格式校验 |
| loguru | >=0.7 | 运行时 | 日志记录 |
| tenacity | >=8.2 | 运行时 | 重试机制（LLM 调用等网络操作容错） |
| APScheduler | >=3.10 | 运行时 | 主动巡检定时调度器（未安装时降级为手动巡检） |
| openai | >=1.30 | 可选（已注释） | LLM + Embedding API 客户端；未安装时系统降级为规则响应 |
| chromadb | >=0.5 | 可选（已注释） | 持久化向量存储；未安装时使用内存哈希嵌入回退 |
| black | >=24.4 | 开发工具 | 代码格式化 |
| flake8 | >=7.0 | 开发工具 | 代码静态检查 |
| pytest | >=8.0 | 开发工具 | 单元测试框架 |
| httpx | >=0.27 | 开发工具 | HTTP 客户端（测试用） |

### 1.2 AI Agent（ai-agent/requirements.txt）

| 依赖 | 版本要求 | 类型 | 用途 |
|------|----------|------|------|
| openai | ==1.35.0 | 可选 | LLM 客户端；Agent 在缺失时降级为规则引擎 |
| loguru | ==0.7.2 | 运行时 | 日志记录 |
| tenacity | ==8.3.0 | 运行时 | 重试机制 |
| Pydantic | ==2.7.4 | 运行时 | 数据验证与 Agent 状态结构定义 |
| PyYAML | ==6.0.1 | 运行时 | YAML 配置与故障模式库解析（`failure_patterns/*.yaml`、`repair_cases/*.yaml`） |
| langgraph | ==0.1.5 | 预留（已注释） | 多智能体工作流编排（预留，当前用纯 Python StateGraph 实现，API 兼容 LangGraph） |
| langchain-core | ==0.2.10 | 预留（已注释） | LangChain 核心库（预留） |
| chromadb | ==0.5.3 | 可选（已注释） | 持久化向量存储；未安装时使用内存存储 + 哈希嵌入 |

### 1.3 车辆协议层（vehicle_protocol/pyproject.toml）

| 依赖 | 版本要求 | 类型 | 用途 |
|------|----------|------|------|
| Pydantic | >=2.7 | 运行时 | 车辆数据 Schema 定义（Pydantic v2 + JSON Schema 导出） |
| setuptools | >=68.0 | 构建工具 | Python 包构建 |
| wheel | — | 构建工具 | Python 分发包格式 |
| pytest | >=8.0 | 开发工具（可选） | 单元测试 |

### 1.4 前端（frontend/package.json）

#### 运行时依赖（dependencies）

| 依赖 | 版本要求 | 用途 |
|------|----------|------|
| React | ^18.3.1 | UI 框架 |
| React DOM | ^18.3.1 | React DOM 渲染器 |
| React Router DOM | ^6.24.1 | 前端路由管理 |
| Ant Design | ^5.20.0 | UI 组件库（表单/表格/图表/布局等） |
| Axios | ^1.7.2 | HTTP 客户端，与后端 API 通信 |
| Zustand | ^4.5.4 | 轻量级状态管理 |
| ECharts | ^6.1.0 | 数据可视化图表库 |
| echarts-for-react | ^3.0.6 | ECharts 的 React 封装 |
| Recharts | ^2.12.7 | React 图表库（补充图表类型） |
| Three.js | ^0.185.1 | 3D 图形库（车辆数字孪生 3D 渲染） |
| @react-three/fiber | ^8.18.0 | Three.js 的 React 渲染器 |
| @react-three/drei | ^9.122.0 | React Three Fiber 辅助工具集 |
| @types/three | ^0.185.3 | Three.js TypeScript 类型定义 |
| Framer Motion | ^12.43.0 | React 动画库 |
| GSAP | ^3.15.0 | 高性能动画库（故事模式过渡动画） |
| Day.js | ^1.11.11 | 轻量级日期处理库 |

#### 开发依赖（devDependencies）

| 依赖 | 版本要求 | 用途 |
|------|----------|------|
| TypeScript | ^5.5.3 | TypeScript 编译器 |
| Vite | ^5.3.3 | 前端构建工具与开发服务器 |
| @vitejs/plugin-react | ^4.3.1 | Vite React 插件 |
| Tailwind CSS | ^3.4.4 | 原子化 CSS 框架 |
| PostCSS | ^8.4.39 | CSS 转换工具 |
| Autoprefixer | ^10.4.19 | CSS 自动添加浏览器前缀 |
| ESLint | ^8.57.0 | JavaScript/TypeScript 代码检查 |
| @typescript-eslint/eslint-plugin | ^7.15.0 | ESLint TypeScript 规则插件 |
| @typescript-eslint/parser | ^7.15.0 | ESLint TypeScript 解析器 |
| eslint-plugin-react-hooks | ^4.6.2 | React Hooks 代码检查规则 |
| eslint-plugin-react-refresh | ^0.4.7 | React Fast Refresh 代码检查规则 |
| Prettier | ^3.3.2 | 代码格式化工具 |
| @types/node | ^20.14.10 | Node.js TypeScript 类型定义 |
| @types/react | ^18.3.3 | React TypeScript 类型定义 |
| @types/react-dom | ^18.3.0 | React DOM TypeScript 类型定义 |

### 1.5 售后闭环新增依赖说明

v2.0 新增的售后闭环功能（§3A.1）未引入任何新的第三方依赖。工单模型（`service_order.py`）使用 SQLAlchemy 内置的 JSON 类型（`SQLAlchemy.dialects.sqlite.JSON` + `SQLAlchemy.types.JSON` 双方言适配），无需额外安装 JSON 扩展库。状态历史字段（`status_history`）直接使用 SQLAlchemy 原生 JSON 列存储，SQLite 与 PostgreSQL 均原生支持。

---

## 二、商业 API 使用

### 2.1 OpenAI API（可选）

| 项目 | 说明 |
|------|------|
| **依赖来源** | `ai-agent/requirements.txt`（`openai==1.35.0`）、`backend/requirements.txt`（`openai>=1.30`，已注释） |
| **使用范围** | ① LLM 诊断增强：Agent 对话增强、专家会诊根因推理、诊断结果自然语言生成；② Embedding 生成：知识库文档向量化（RAG 检索） |
| **是否必需** | 否（可选）。系统在未配置 `OPENAI_API_KEY` 时自动降级 |
| **降级方案** | 无 API Key 时走规则路径：阈值表（传感器阈值检测）+ 故障模式库（`failure_patterns/*.yaml` 模式匹配）+ 模板生成（诊断报告模板）。各子 Agent 及专家内部 try/except 降级为规则响应，保证核心功能不中断 |
| **调用方式** | 通过 `ai-agent` 模块封装，backend 经统一适配层调用，不在 API 接口层直接调用 LLM |
| **数据流向** | 仅发送车辆传感器模拟数据与诊断上下文，不发送用户个人隐私信息 |

### 2.2 调用环节明细

OpenAI API 在系统中的调用环节与触发条件：

| 调用环节 | 触发条件 | 调用模型 | 输入 Token 估算 | 输出 Token 估算 |
|----------|----------|----------|:---:|:---:|
| Agent 对话增强 | 用户发送聊天消息 | GPT-4o-mini | ~800 | ~400 |
| 专家会诊根因推理 | 检测到异常触发专家会诊 | GPT-4o-mini | ~1,200 | ~600 |
| 诊断报告自然语言生成 | 诊断流程完成 | GPT-4o-mini | ~500 | ~300 |
| 知识库 Embedding | 知识库文档入库时（一次性） | text-embedding-3-small | ~2,000/文档 | — |

### 2.3 费用假设与成本测算

基于 OpenAI 公开定价（2026-08），对 Demo 与生产场景的费用进行测算：

#### 定价基准

| 模型 | 输入价格 | 输出价格 | Embedding 价格 |
|------|----------|----------|----------------|
| GPT-4o-mini | $0.15 / 1M tokens | $0.60 / 1M tokens | — |
| text-embedding-3-small | — | — | $0.02 / 1M tokens |

#### Demo 场景成本（比赛演示）

| 场景 | 调用次数 | 输入 Token | 输出 Token | 费用估算 |
|------|----------|------------|------------|----------|
| 单次完整 Demo 演示（5 轮对话 + 1 次会诊 + 1 次报告） | 7 次 LLM | ~7,100 | ~3,100 | ≈ $0.003 |
| Embedding 建库（一次性，~20 篇文档） | 20 次 | ~40,000 | — | ≈ $0.001 |
| **单次 Demo 总成本** | — | — | — | **≈ $0.004（约 ¥0.03）** |

#### 生产场景成本（预估）

| 场景 | 日均调用量 | 日均费用 | 月均费用 |
|------|------------|----------|----------|
| 单车日守护（2 次对话 + 0.5 次会诊 + 0.5 次报告） | 3 次 | ≈ $0.001 | ≈ $0.03 |
| 100 车队规模 | 300 次 | ≈ $0.13 | ≈ $3.9 |
| 1,000 车队规模 | 3,000 次 | ≈ $1.29 | ≈ $38.7 |

> **结论**：GPT-4o-mini 成本极低，单车月均费用约 ¥0.2，100 车队月均约 ¥28。即使 1,000 车队规模，月均费用也不足 ¥300，商业可行性高。Embedding 建库为一次性成本，可忽略。

### 2.4 降级机制说明

系统的离线降级策略确保在无任何商业 API 的情况下仍可完整运行：

| 场景 | 有 API Key | 无 API Key |
|------|-----------|------------|
| 感知层（perception） | 语义检测 + 阈值检测 | 纯阈值检测 |
| 诊断层（diagnosis） | LLM 根因增强 + 专家会诊 | 规则引擎 + 专家知识库模式匹配 |
| 风险层（risk） | LLM 辅助量化 | 规则量化（等级/概率/ETA） |
| 解释层（explainer） | 自然语言生成 | 模板生成 |
| 知识库检索（RAG） | OpenAI Embedding + 向量检索 | 内存哈希嵌入 + 相似度匹配 |

> 降级状态在前端 UI 中明确标识，用户可知晓当前运行在规则模式还是 LLM 增强模式。

---

## 三、闭源模型使用范围

### 3.1 OpenAI GPT-4o-mini（可选）

| 项目 | 说明 |
|------|------|
| **模型名称** | GPT-4o-mini |
| **提供方** | OpenAI |
| **是否开源** | 否（闭源模型，通过 API 调用） |
| **使用场景** | ① Agent 对话增强：自然语言交互、多轮对话理解；② 诊断结果自然语言生成：将结构化诊断结论转化为用户可读的报告；③ 专家会诊根因推理：辅助分析传感器趋势与故障关联 |
| **是否必需** | 否（完全可选） |
| **可替代性** | **完全可替代**。离线规则路径覆盖全部核心功能：感知（阈值检测）、诊断（故障模式库匹配）、风险（规则量化）、解释（模板生成）、知识检索（哈希嵌入）。移除 GPT-4o-mini 后系统核心闭环不受影响，仅自然语言表达丰富度降低 |
| **数据隐私** | 仅发送车辆传感器模拟数据与诊断上下文至 API，不涉及真实用户隐私数据。Demo 阶段全部数据为模拟生成 |

### 3.2 其他闭源模型

| 模型 | 使用情况 |
|------|----------|
| OpenAI Embedding 模型 | 可选，用于知识库文档向量化。未配置时使用内存哈希嵌入回退 |
| 其他第三方闭源模型 | 无 |

---

## 四、本地模型替代方案

### 4.1 方案概述

为进一步降低对 OpenAI API 的依赖，系统规划了**本地小模型兜底方案**（对应开发计划 W2.4），在无网无 Key 环境下仍可走 LLM 路径而非纯规则：

| 方案 | 模型 | 参数量 | 硬件要求 | 状态 |
|------|------|--------|----------|------|
| 方案 A（推荐） | Qwen2.5-7B-Instruct | 7B | 8GB+ VRAM GPU 或 16GB+ RAM CPU | 规划中（W2.4） |
| 方案 B | Qwen2.5-3B-Instruct | 3B | 4GB+ VRAM GPU 或 8GB+ RAM CPU | 规划中（W2.4） |
| 方案 C | Llama 3.1-8B-Instruct | 8B | 8GB+ VRAM GPU | 备选 |

### 4.2 接入方式

本地模型通过 **Ollama** 运行时加载，系统通过 OpenAI 兼容 API（`openai` 库的 `base_url` 参数指向 `http://localhost:11434/v1`）无缝切换，无需修改业务代码：

```python
# 当前（OpenAI 云端）
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# 本地模型（Ollama，零代码改动）
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
```

### 4.3 能力对照

| 能力维度 | OpenAI GPT-4o-mini | Qwen2.5-7B（本地） | 纯规则引擎（无 LLM） |
|----------|:-:|:-:|:-:|
| 自然语言对话 | 优秀 | 良好 | 不支持（模板回复） |
| 根因推理 | 优秀 | 良好 | 模式匹配（有限） |
| 报告生成 | 优秀 | 良好 | 模板生成（可用） |
| 响应时延 | 1-3s（网络） | 2-8s（本地） | <100ms |
| 离线可用 | 否 | 是 | 是 |
| 费用 | $0.003/次 | 免费 | 免费 |

> **结论**：本地模型方案在离线场景下提供接近云端的 LLM 能力，是「无网无 Key」场景的最佳兜底。决策时延增加（2-8s vs 1-3s）在车辆守护场景可接受（非实时控制）。

---

## 五、锁定风险分析

### 5.1 供应商锁定评估

| 锁定维度 | 风险等级 | 分析 |
|----------|:--------:|------|
| **API 接口锁定** | 低 | 系统通过 `openai` 库调用，该库支持 `base_url` 参数，可无缝切换至 Ollama / vLLM / LM Studio 等本地推理引擎。业务代码不直接拼接 HTTP 请求 |
| **模型能力锁定** | 低 | 系统的 Prompt 模板与故障模式库为通用设计，不依赖 GPT-4o-mini 特有能力（如 function calling 特定格式）。切换至 Qwen/Llama 时仅需微调提示词 |
| **数据格式锁定** | 极低 | 输入输出均为标准 JSON，无 OpenAI 专有数据格式。Embedding 向量存储使用 ChromaDB（开源），不绑定 OpenAI Embedding 专有格式 |
| **计费锁定** | 极低 | 按量付费，无最低消费、无长期合约。可随时停用，系统自动降级为规则引擎 |
| **生态锁定** | 极低 | 系统不使用 LangChain/LangGraph 的 Agent 编排（已注释为预留），使用自研 StateGraph，无框架级锁定 |

### 5.2 迁移路径

从 OpenAI API 迁移至本地模型的步骤：

| 步骤 | 工作量 | 说明 |
|------|--------|------|
| 1. 安装 Ollama + 拉取模型 | 0.5h | `ollama pull qwen2.5:7b` |
| 2. 修改环境变量 | 5min | `OPENAI_BASE_URL=http://localhost:11434/v1` |
| 3. 微调 Prompt 模板（如需） | 2h | 本地模型可能需要更明确的指令格式 |
| 4. 验证核心链路 | 1h | 对话/会诊/报告生成回归测试 |
| **总迁移工作量** | **< 0.5 天** | 零代码改动，仅配置变更 |

### 5.3 风险缓解措施

1. **抽象层隔离**：所有 LLM 调用通过 `ai-agent` 模块统一封装，业务层不直接依赖 OpenAI SDK。
2. **双模式测试**：CI 流水线同时测试「有 Key」与「无 Key」两条路径，确保降级路径始终可用。
3. **Prompt 解耦**：专家会诊 Prompt 模板存储为 YAML 文件（`failure_patterns/*.yaml`），可独立于代码修改。
4. **Embedding 可替换**：知识库检索层使用 ChromaDB 抽象接口，Embedding 模型可从 OpenAI 切换至本地 Sentence-Transformers。

---

## 六、第三方服务

| 服务 | 使用情况 |
|------|----------|
| 云数据库服务 | 无。开发环境使用 SQLite 本地存储，生产环境支持私有化部署（PostgreSQL） |
| 云存储服务 | 无 |
| 消息推送服务 | 无。Demo 阶段的推送提醒为模拟展示，不调用真实推送服务 |
| 地图/定位服务 | 无 |
| 支付服务 | 无 |
| 身份认证服务（OAuth 等） | 无。使用自建 JWT 认证 |
| 外部 API 网关 | 无 |
| 其他任何外部服务 | 无 |

> **结论**：Demo 阶段不依赖任何外部服务。系统完全自包含运行，可离线部署。

---

## 七、开源依赖 License 清单

### 7.1 后端依赖 License

| 依赖 | License | 是否宽松 | 合规状态 |
|------|---------|:--------:|:--------:|
| FastAPI | MIT | 是 | 合规 |
| Uvicorn | BSD-3-Clause | 是 | 合规 |
| python-multipart | Apache-2.0 | 是 | 合规 |
| Pydantic | MIT | 是 | 合规 |
| pydantic-settings | MIT | 是 | 合规 |
| python-dotenv | BSD-3-Clause | 是 | 合规 |
| SQLAlchemy | MIT | 是 | 合规 |
| psycopg | LGPL-3.0 | 是（动态链接） | 合规 |
| passlib | BSD-3-Clause | 是 | 合规 |
| python-jose | MIT | 是 | 合规 |
| email-validator | CC0-1.0 | 是（公有领域） | 合规 |
| loguru | MIT | 是 | 合规 |
| tenacity | Apache-2.0 | 是 | 合规 |
| APScheduler | MIT | 是 | 合规 |
| openai | MIT | 是 | 合规 |
| chromadb | Apache-2.0 | 是 | 合规 |
| black | MIT | 是 | 合规 |
| flake8 | MIT | 是 | 合规 |
| pytest | MIT | 是 | 合规 |
| httpx | BSD-3-Clause | 是 | 合规 |

### 7.2 AI Agent 依赖 License

| 依赖 | License | 合规状态 |
|------|---------|:--------:|
| openai | MIT | 合规 |
| loguru | MIT | 合规 |
| tenacity | Apache-2.0 | 合规 |
| Pydantic | MIT | 合规 |
| PyYAML | MIT | 合规 |
| langgraph（预留） | MIT | 合规 |
| langchain-core（预留） | MIT | 合规 |
| chromadb（可选） | Apache-2.0 | 合规 |

### 7.3 车辆协议层依赖 License

| 依赖 | License | 合规状态 |
|------|---------|:--------:|
| Pydantic | MIT | 合规 |
| setuptools | MIT | 合规 |
| wheel | MIT | 合规 |
| pytest | MIT | 合规 |

### 7.4 前端依赖 License

| 依赖 | License | 合规状态 |
|------|---------|:--------:|
| React | MIT | 合规 |
| React DOM | MIT | 合规 |
| React Router DOM | MIT | 合规 |
| Ant Design | MIT | 合规 |
| Axios | MIT | 合规 |
| Zustand | MIT | 合规 |
| ECharts | Apache-2.0 | 合规 |
| echarts-for-react | MIT | 合规 |
| Recharts | MIT | 合规 |
| Three.js | MIT | 合规 |
| @react-three/fiber | MIT | 合规 |
| @react-three/drei | MIT | 合规 |
| Framer Motion | MIT | 合规 |
| GSAP | "Standard" / GreenSock No-Charge License | 合规（免费商用） |
| Day.js | MIT | 合规 |
| TypeScript | Apache-2.0 | 合规 |
| Vite | MIT | 合规 |
| Tailwind CSS | MIT | 合规 |
| ESLint | MIT | 合规 |
| Prettier | MIT | 合规 |

> **结论**：全部开源依赖均使用 MIT / BSD / Apache 等宽松许可证，无 GPL / AGPL 等 Copyleft 许可证，商业使用无合规风险。GSAP 使用 GreenSock 免费许可证，允许商业使用。

---

## 八、依赖合规总结

| 类别 | 数量 | 是否必需 | 合规说明 |
|------|------|----------|----------|
| 开源依赖（后端） | 14 个运行时 + 4 个开发工具 | 必需 | 全部为成熟开源库，MIT/BSD/Apache 等宽松许可证 |
| 开源依赖（AI Agent） | 4 个运行时 + 1 个可选 | 必需/可选 | openai 为可选，缺失时降级 |
| 开源依赖（车辆协议层） | 1 个运行时 | 必需 | Pydantic，MIT 许可证 |
| 开源依赖（前端） | 16 个运行时 + 15 个开发工具 | 必需 | 全部为成熟前端开源生态 |
| 商业 API | 1 个（OpenAI API） | 可选 | 缺失时降级为规则路径；单车月均成本 ≈ ¥0.2 |
| 闭源模型 | 1 个（GPT-4o-mini） | 可选 | 完全可替代，离线规则路径覆盖全部核心功能 |
| 本地模型替代 | 1 个（Qwen2.5-7B，规划中） | 可选 | 无网无 Key 场景的 LLM 兜底方案 |
| 第三方服务 | 0 个 | — | Demo 阶段不依赖任何外部服务 |

### 8.1 核心合规要点

1. **所有商业 API 与闭源模型均为可选**：系统在完全离线、零外部依赖的情况下仍可完整运行核心功能闭环。
2. **降级透明**：降级状态在前端 UI 明确标识，用户可知晓当前运行模式。
3. **无数据外泄风险**：Demo 阶段全部数据为模拟生成，且第三方服务依赖为零。
4. **开源优先**：运行时核心依赖全部为开源库，可审计、可替换。
5. **无锁定风险**：API 抽象层隔离 + 标准接口 + 可配置 base_url，迁移至本地模型工作量 < 0.5 天。
6. **成本可控**：GPT-4o-mini 单次 Demo 成本 ≈ ¥0.03，100 车队月均 ≈ ¥28，商业可行。

---

*CarSoul Guardian © 2024-2026 · 第三方依赖披露版本 v2.0 · 最后更新：2026-08-04*
