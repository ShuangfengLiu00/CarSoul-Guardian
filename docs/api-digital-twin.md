# CarSoul Guardian — 数字生命引擎 API（TASK007-V2）

Base URL: `http://localhost:8000`

> 本文档覆盖 TASK007-V2 车辆数字生命核心引擎（Vehicle Digital Life Engine）的全部 RESTful 接口。
> 所有接口统一前缀 `/api/digital-twin`，返回 JSON 格式，时间字段使用 ISO 8601。

---

## 目录

| # | 接口 | 方法 | 说明 |
|---|------|------|------|
| 1 | `/create` | POST | 创建数字生命 |
| 2 | `/{id}/profile` | GET | 灵魂档案（旗舰聚合视图） |
| 3 | `/{id}/soul-score` | GET | VSS 灵魂指数 |
| 4 | `/{id}/soul-history` | GET | VSS 历史轨迹 |
| 5 | `/{id}/life-state` | GET | 生命状态 |
| 6 | `/{id}/life-state/refresh` | POST | 刷新生命状态 |
| 7 | `/{id}/life-events` | GET/POST | 生命事件时间线 |
| 8 | `/{id}/memories` | GET/POST | 车辆记忆系统 |
| 9 | `/{id}/memories/search` | GET | 记忆搜索 |
| 10 | `/{id}/health-metrics` | GET/POST | 组件健康指标 |
| 11 | `/{id}/predictions` | GET/POST | AI 预测 |
| 12 | `/{id}/driver-profile` | GET | 驾驶人格 |
| 13 | `/{id}/driver-profile/refresh` | POST | 刷新驾驶人格 |
| 14 | `/{id}/agent/{agent_type}` | POST | Agent 统一查询接口 |
| 15 | `/{id}/generate-lifecycle` | POST | 365天生命周期生成器 |

---

## 1. 创建数字生命

### POST `/api/digital-twin/create`

为车辆生成灵魂 ID 并初始化生命状态。

**Query 参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `vehicle_id` | int | 是 | 车辆 ID |

**响应 `201`：**
```json
{
  "vehicle_id": 1,
  "soul_id": "CSG-2026-00001",
  "message": "数字生命已创建",
  "identity": {
    "id": 1,
    "vehicle_id": 1,
    "vehicle_uuid": "CSG-2026-00001",
    "vin": "LSJW32E78PD000017",
    "brand": "Tesla",
    "model": "Model Y",
    "production_year": 2024,
    "energy_type": "electric",
    "vehicle_class": "SUV",
    "owner_id": 1,
    "birth_time": "2024-03-15T00:00:00",
    "nickname": "小白",
    "created_at": "2026-07-29T10:00:00"
  }
}
```

---

## 2. 灵魂档案（旗舰聚合视图）

### GET `/api/digital-twin/{vehicle_id}/profile`

获取车辆数字生命灵魂档案 — 聚合所有数字生命数据的旗舰视图。

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `vehicle_id` | int | 车辆 ID |

**响应 `200`：**
```json
{
  "soul_id": "CSG-2026-00001",
  "vehicle_id": 1,
  "name": "Tesla Model Y",
  "brand": "Tesla",
  "model": "Model Y",
  "year": 2024,
  "energy_type": "electric",
  "nickname": "小白",
  "soul_score": 88.5,
  "soul_grade": "excellent",
  "soul_grade_label": "优秀状态",
  "soul_breakdown": {
    "health": 85.0,
    "memory": 72.0,
    "maintenance": 90.0,
    "driving": 82.0,
    "prediction": 88.0,
    "health_contribution": 34.0,
    "memory_contribution": 10.8,
    "maintenance_contribution": 13.5,
    "driving_contribution": 12.3,
    "prediction_contribution": 13.2
  },
  "life_stage": "MATURE",
  "life_stage_label": "成熟期",
  "health_score": 85.0,
  "energy_health": 88.0,
  "mechanical_health": 84.0,
  "software_health": 95.0,
  "companion_days": 726,
  "mileage": 35000,
  "mileage_label": "35,000 km",
  "life_events": [],
  "life_events_count": 38,
  "memories": [],
  "memories_count": 126,
  "health_metrics": [],
  "predictions": [],
  "driver_profile": {
    "id": 1,
    "vehicle_id": 1,
    "driver_style": "balanced",
    "aggressive_score": 25.0,
    "comfort_score": 85.0,
    "eco_score": 78.0,
    "total_trips": 240,
    "total_distance": 8400.5,
    "total_duration": 18000,
    "total_harsh_events": 12,
    "preferred_speed_range": "60-80 km/h",
    "preferred_driving_time": "evening",
    "preferred_road_type": "urban",
    "updated_at": "2026-07-29T10:00:00"
  },
  "driver_style_label": "稳健型",
  "ai_insights": [
    "电池健康度良好，预计可继续使用3年以上",
    "刹车片磨损接近70%，建议下次保养时检查"
  ],
  "agent_hooks": {
    "ai_doctor": { "status": "available", "endpoint": "/api/digital-twin/{id}/agent/doctor" },
    "ai_maintenance": { "status": "available", "endpoint": "/api/digital-twin/{id}/agent/maintenance" },
    "ai_insurance": { "status": "available", "endpoint": "/api/digital-twin/{id}/agent/insurance" }
  }
}
```

---

## 3. VSS 灵魂指数

### GET `/api/digital-twin/{vehicle_id}/soul-score`

计算车辆灵魂指数 VSS。

**公式：** `VSS = Health × 40% + Memory × 15% + Maintenance × 15% + Driving × 15% + Prediction × 15%`

**响应 `200`：**
```json
{
  "vehicle_id": 1,
  "soul_id": "CSG-2026-00001",
  "score": 88.5,
  "grade": "excellent",
  "grade_label": "优秀状态",
  "breakdown": {
    "health": 85.0,
    "memory": 72.0,
    "maintenance": 90.0,
    "driving": 82.0,
    "prediction": 88.0,
    "health_contribution": 34.0,
    "memory_contribution": 10.8,
    "maintenance_contribution": 13.5,
    "driving_contribution": 12.3,
    "prediction_contribution": 13.2
  },
  "computed_at": "2026-07-29T10:00:00"
}
```

**VSS 等级：**

| 分数范围 | 等级 | 标签 |
|----------|------|------|
| 95-100 | legendary | 传奇状态 |
| 80-95 | excellent | 优秀状态 |
| 60-80 | normal | 正常状态 |
| <60 | risk | 风险状态 |

---

## 4. VSS 历史轨迹

### GET `/api/digital-twin/{vehicle_id}/soul-history`

获取 VSS 灵魂指数历史记录。

**Query 参数：**

| 参数 | 类型 | 默认 | 范围 | 说明 |
|------|------|------|------|------|
| `limit` | int | 30 | 1-365 | 返回记录数 |

**响应 `200`：**
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "soul_score": 92.0,
      "health_score": 90.0,
      "memory_score": 80.0,
      "maintenance_score": 95.0,
      "driving_score": 88.0,
      "prediction_score": 90.0,
      "grade": "excellent",
      "notes": null,
      "recorded_at": "2026-07-01T00:00:00"
    }
  ],
  "total": 1
}
```

---

## 5. 生命状态

### GET `/api/digital-twin/{vehicle_id}/life-state`

获取车辆当前生命状态。

**响应 `200`：**
```json
{
  "id": 1,
  "vehicle_id": 1,
  "health_score": 85.0,
  "life_stage": "MATURE",
  "mileage": 35000,
  "vehicle_age_days": 726,
  "energy_health": 88.0,
  "mechanical_health": 84.0,
  "software_health": 95.0,
  "soul_score": 88.5,
  "updated_at": "2026-07-29T10:00:00"
}
```

**生命阶段：**

| 阶段 | 说明 |
|------|------|
| NEW | 新生期 |
| GROWTH | 成长期 |
| MATURE | 成熟期 |
| AGING | 老化期 |
| RETIRE | 退役期 |

---

## 6. 刷新生命状态

### POST `/api/digital-twin/{vehicle_id}/life-state/refresh`

重新计算生命阶段和灵魂指数。

**响应 `200`：** 同 [生命状态](#5-生命状态) 响应格式。

---

## 7. 生命事件时间线

### GET `/api/digital-twin/{vehicle_id}/life-events`

获取车辆生命事件时间线。

**Query 参数：**

| 参数 | 类型 | 默认 | 范围 | 说明 |
|------|------|------|------|------|
| `event_type` | string | - | - | 可选，按类型过滤 |
| `limit` | int | 50 | 1-200 | 返回记录数 |

**事件类型：** `PURCHASE` | `FIRST_DRIVE` | `TRAVEL` | `MAINTENANCE` | `ACCIDENT` | `WARNING` | `RECOVERY` | `UPGRADE` | `CUSTOM`

**响应 `200`：**
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "event_type": "TRAVEL",
      "title": "第一次长途旅行",
      "description": "车辆陪伴主人完成北京到天津往返",
      "importance": 8,
      "mileage": 250,
      "location": "北京→天津",
      "cost": null,
      "extra_data": null,
      "event_time": "2024-04-20T10:00:00",
      "created_at": "2024-04-20T10:00:00"
    }
  ],
  "total": 1
}
```

### POST `/api/digital-twin/{vehicle_id}/life-events`

创建车辆生命事件。

**请求体：**
```json
{
  "event_type": "TRAVEL",
  "title": "周末郊游",
  "description": "前往莫干山度周末",
  "importance": 7,
  "mileage": 180,
  "location": "上海→莫干山",
  "cost": null,
  "event_time": "2026-07-28T08:00:00"
}
```

**响应 `201`：** 返回创建的事件对象。

---

## 8. 车辆记忆系统

### GET `/api/digital-twin/{vehicle_id}/memories`

获取车辆记忆列表。

**Query 参数：**

| 参数 | 类型 | 默认 | 范围 | 说明 |
|------|------|------|------|------|
| `memory_type` | string | - | - | 可选，按类型过滤 |
| `limit` | int | 50 | 1-200 | 返回记录数 |

**记忆类型：** `habit` | `event` | `preference` | `warning` | `recovery` | `emotion` | `context`

**响应 `200`：**
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "memory_type": "habit",
      "content": "主人习惯晚上10点后驾驶",
      "emotion_score": 0.2,
      "importance": 6,
      "source": "system",
      "meta_data": null,
      "created_time": "2024-06-15T22:00:00"
    }
  ],
  "total": 1
}
```

### POST `/api/digital-twin/{vehicle_id}/memories`

创建车辆记忆 — 让 AI 积累对车辆的认知。

**请求体：**
```json
{
  "memory_type": "preference",
  "content": "主人喜欢开启座椅加热",
  "emotion_score": 0.5,
  "importance": 5,
  "source": "system"
}
```

**响应 `201`：** 返回创建的记忆对象。

---

## 9. 记忆搜索

### GET `/api/digital-twin/{vehicle_id}/memories/search`

AI 上下文检索 — 按关键词搜索车辆记忆。

**Query 参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `q` | string | 是 | 搜索关键词 |
| `limit` | int | - | 默认 20，范围 1-100 |

**响应 `200`：** 同 [车辆记忆系统](#8-车辆记忆系统) 响应格式。

---

## 10. 组件健康指标

### GET `/api/digital-twin/{vehicle_id}/health-metrics`

获取组件级细分健康指标。

**Query 参数：**

| 参数 | 类型 | 默认 | 范围 | 说明 |
|------|------|------|------|------|
| `component` | string | - | - | 可选，按组件过滤 |
| `limit` | int | 50 | 1-200 | 返回记录数 |

**组件：** `battery` | `motor` | `brake` | `tire` | `body` | `electronics` | `cooling` | `engine`

**响应 `200`：**
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "component": "battery",
      "health_score": 90.0,
      "temperature": 35.0,
      "wear_level": 10.0,
      "risk_level": "low",
      "record_time": "2026-07-29T10:00:00"
    }
  ],
  "total": 1
}
```

### POST `/api/digital-twin/{vehicle_id}/health-metrics`

记录车辆健康指标。

**请求体：**
```json
{
  "component": "brake",
  "health_score": 75.0,
  "temperature": 45.0,
  "wear_level": 65.0,
  "risk_level": "medium"
}
```

**响应 `201`：** 返回创建的健康指标对象。

---

## 11. AI 预测

### GET `/api/digital-twin/{vehicle_id}/predictions`

获取 AI 预测结果列表。

**Query 参数：**

| 参数 | 类型 | 默认 | 范围 | 说明 |
|------|------|------|------|------|
| `status` | string | - | - | 可选，按状态过滤 |
| `limit` | int | 20 | 1-100 | 返回记录数 |

**响应 `200`：**
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "target_component": "brake",
      "prediction": "未来3000公里刹车片磨损达到70%",
      "risk_level": "medium",
      "confidence": 0.87,
      "predicted_value": 3000,
      "predicted_unit": "km",
      "predicted_time": null,
      "root_cause": "刹车片使用里程接近更换周期",
      "suggestion": "建议下次保养时检查并更换刹车片",
      "status": "active",
      "actual_outcome": null,
      "prediction_time": "2026-07-29T10:00:00",
      "created_at": "2026-07-29T10:00:00"
    }
  ],
  "total": 1
}
```

### POST `/api/digital-twin/{vehicle_id}/predictions`

创建 AI 预测结果。

**请求体：**
```json
{
  "target_component": "tire",
  "prediction": "前轮胎纹深度将在5000公里后低于安全阈值",
  "risk_level": "high",
  "confidence": 0.82,
  "predicted_value": 5000,
  "predicted_unit": "km",
  "root_cause": "前轮胎纹磨损速率高于平均值",
  "suggestion": "建议更换前轮轮胎或前后对调"
}
```

**响应 `201`：** 返回创建的预测对象。

---

## 12. 驾驶人格

### GET `/api/digital-twin/{vehicle_id}/driver-profile`

获取驾驶人格模型。

**响应 `200`：**
```json
{
  "id": 1,
  "vehicle_id": 1,
  "driver_style": "balanced",
  "aggressive_score": 25.0,
  "comfort_score": 85.0,
  "eco_score": 78.0,
  "total_trips": 240,
  "total_distance": 8400.5,
  "total_duration": 18000,
  "total_harsh_events": 12,
  "preferred_speed_range": "60-80 km/h",
  "preferred_driving_time": "evening",
  "preferred_road_type": "urban",
  "updated_at": "2026-07-29T10:00:00"
}
```

**驾驶风格：** `aggressive`（激进型）| `balanced`（稳健型）| `eco`（节能型）| `sporty`（运动型）

---

## 13. 刷新驾驶人格

### POST `/api/digital-twin/{vehicle_id}/driver-profile/refresh`

从驾驶行为数据重新计算驾驶人格。

**响应 `200`：** 同 [驾驶人格](#12-驾驶人格) 响应格式。

---

## 14. Agent 统一查询接口

### POST `/api/digital-twin/{vehicle_id}/agent/{agent_type}`

AI Agent 统一查询接口 — 基于灵魂档案的规则化响应。

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `vehicle_id` | int | 车辆 ID |
| `agent_type` | string | Agent 类型：`doctor` \| `maintenance` \| `insurance` |

**请求体：**
```json
{
  "query": "请给出当前车辆的全面分析报告。",
  "agent_type": "doctor",
  "context": null
}
```

**响应 `200`：**
```json
{
  "agent_type": "doctor",
  "answer": "我是您的AI车辆医生。Tesla Model Y 的当前灵魂指数为 88.5（优秀状态）。\n生命阶段: 成熟期，整体健康: 85.0。\n各组件健康状态:\n  · battery: 90 (风险: low)\n  · brake: 75 (风险: medium)\n...\n活跃预测:\n  · 未来3000公里刹车片磨损达到70% (可信度: 0.87)",
  "confidence": 0.85,
  "suggestions": [
    "电池健康度良好，预计可继续使用3年以上",
    "刹车片磨损接近70%，建议下次保养时检查"
  ],
  "data": {
    "soul_score": 88.5,
    "life_stage": "MATURE",
    "health_score": 85.0
  }
}
```

**Agent 类型说明：**

| Agent | 说明 | 输出内容 |
|-------|------|----------|
| `doctor` | AI 车辆医生 | 健康诊断、组件状态、活跃预测 |
| `maintenance` | AI 维修顾问 | 维护质量评分、高风险预测、维护建议 |
| `insurance` | AI 保险顾问 | 风险评估、保费方案建议 |

---

## 15. 365天生命周期生成器

### POST `/api/digital-twin/{vehicle_id}/generate-lifecycle`

生成 365 天完整数字生命周期数据 — 健康指标、传感器、生命事件、记忆、预测、VSS。

**Query 参数：**

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `force` | bool | false | 强制重新生成（覆盖现有数据） |

**响应 `200`：**
```json
{
  "vehicle_id": 1,
  "message": "已生成365天数字生命周期数据",
  "days": 365,
  "health_metrics": 2555,
  "sensor_readings": 4380,
  "life_events": 42,
  "memories": 126,
  "predictions": 8,
  "total_mileage": 12775,
  "total_trips": 365,
  "total_distance": 12775.0,
  "total_harsh_events": 24,
  "skipped": false
}
```

如果已有数据且 `force=false`：
```json
{
  "vehicle_id": 1,
  "message": "车辆已有生命周期数据，跳过生成。使用 force=true 可重新生成。",
  "skipped": true
}
```

---

## 数据库表结构

| # | 表名 | 说明 |
|---|------|------|
| 1 | `vehicle_identity` | 车辆数字身份（出生证明） |
| 2 | `vehicle_life_state` | 车辆当前生命状态 |
| 3 | `vehicle_health_metrics` | 组件级健康指标 |
| 4 | `vehicle_sensor_stream` | 传感器时间序列 |
| 5 | `vehicle_life_event` | 生命事件（核心） |
| 6 | `vehicle_memory` | 车辆记忆系统 |
| 7 | `driver_profile` | 驾驶人格模型 |
| 8 | `vehicle_prediction` | AI 预测结果 |
| 9 | `vehicle_soul_score_history` | VSS 历史记录 |

迁移文件：`backend/migrations/20260729_01_create_digital_life_engine.sql`

---

## 前端绑定

| 页面 | 路由 | 绑定接口 |
|------|------|----------|
| My CarSoul（灵魂主页） | `/soul` | `/profile`, `/generate-lifecycle`, `/agent/{type}` |
| 数字生命（VehicleLifeHome） | `/life` | `/api/vehicle/{id}/life-record` |

**My CarSoul 页面展示：**
- Soul Hero：灵魂 ID + VSS + 生命阶段 + 陪伴天数
- Vitals Row：陪伴时间、行驶里程、生命事件、AI记忆、整体健康、驾驶人格
- VSS Breakdown：5 维度权重分解图
- Health Metrics：组件级健康进度条
- Life Events Timeline：生命事件时间线
- Memories Panel：车辆记忆卡片
- Predictions Panel：AI 预测列表
- AI Insights：AI 洞察建议
- Agent Hooks：三种 Agent 快捷查询入口
