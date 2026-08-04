# CarSoul Guardian API 契约（TASK007 完整版）

Base URL: `http://localhost:8000`

> 本文档覆盖 TASK007 车辆数字生命档案系统的全部 RESTful 接口。
> 所有业务接口统一前缀 `/api`，返回 JSON 格式，时间字段使用 ISO 8601。

---

## 1. 健康检查

| Method | Path | 说明 |
|--------|------|------|
| GET | `/health` | 服务存活探针 |
| GET | `/` | 项目信息 |

---

## 2. 用户接口 `/api/user`

### POST `/api/user/register`
注册新用户。

请求体：
```json
{ "username": "string", "password": "string", "email": "string" }
```
响应 `201`：
```json
{ "id": 1, "username": "string", "email": "string" }
```

### POST `/api/user/login`
用户登录，返回 JWT。

请求体：
```json
{ "username": "string", "password": "string" }
```
响应 `200`：
```json
{ "access_token": "string", "token_type": "bearer", "username": "string" }
```

---

## 3. 车辆接口 `/api/vehicle`

车辆是数字生命档案的根实体。以下接口覆盖车辆 CRUD 和完整档案聚合。

### 3.1 车辆 CRUD

#### GET `/api/vehicle`
返回车辆列表。

响应 `200`：
```json
{
  "items": [
    {
      "id": 1,
      "owner_id": 1,
      "brand": "Tesla",
      "model": "Model Y",
      "year": 2024,
      "vin": "LSJW32E78PD000017",
      "plate_number": "沪A·D2024",
      "color": "珍珠白",
      "nickname": "小白",
      "engine_type": null,
      "fuel_type": "electric",
      "displacement": null,
      "battery_capacity": 60.0,
      "mileage": 12800,
      "status": "active",
      "purchase_date": "2024-03-15",
      "purchase_price": 263900.0,
      "dealer": "特斯拉上海体验中心",
      "insurance_company": "中国人保",
      "insurance_policy_no": "PAX2024001",
      "insurance_expiry": "2026-03-14",
      "registration_date": "2024-03-20",
      "inspection_expiry": "2028-03-20",
      "twin_model_id": null,
      "twin_last_sync": null,
      "avatar_url": null,
      "notes": null,
      "created_at": "2024-03-15T10:00:00",
      "updated_at": "2024-03-15T10:00:00"
    }
  ],
  "total": 1
}
```

#### POST `/api/vehicle`
创建车辆档案。

请求体：
```json
{
  "brand": "Tesla",
  "model": "Model Y",
  "year": 2024,
  "vin": "LSJW32E78PD000017",
  "plate_number": "沪A·D2024",
  "fuel_type": "electric",
  "mileage": 0,
  "color": "珍珠白",
  "nickname": "小白",
  "purchase_date": "2024-03-15"
}
```
响应 `201`：返回完整 `VehicleOut` 对象。

#### GET `/api/vehicle/{vehicle_id}`
获取单辆车辆信息。

响应 `200`：返回完整 `VehicleOut` 对象。
响应 `404`：`{ "detail": "Vehicle not found" }`

#### PUT `/api/vehicle/{vehicle_id}`
更新车辆信息（部分更新，所有字段可选）。

请求体示例：
```json
{ "mileage": 13500, "nickname": "大白" }
```
响应 `200`：返回更新后的 `VehicleOut` 对象。

#### DELETE `/api/vehicle/{vehicle_id}`
删除车辆及其关联数据。

响应 `204`：无内容。
响应 `404`：`{ "detail": "Vehicle not found" }`

---

### 3.2 数字生命档案聚合

#### GET `/api/vehicle/{vehicle_id}/archive`
**核心接口** — 返回车辆完整数字生命档案，聚合所有子实体。

响应 `200`：
```json
{
  "vehicle": { /* VehicleOut */ },
  "lifecycle_events": [ /* LifecycleEventOut[] */ ],
  "latest_health": { /* HealthSnapshotOut | null */ },
  "health_history": [ /* HealthSnapshotOut[] (最近20条) */ ],
  "maintenance_records": [ /* MaintenanceRecordOut[] */ ],
  "maintenance_schedules": [ /* MaintenanceScheduleOut[] */ ],
  "driving_behaviors": [ /* DrivingBehaviorOut[] (最近30天) */ ],
  "alerts": [ /* AlertOut[] */ ],
  "ownership_history": [ /* OwnershipRecordOut[] */ ],
  "digital_twin": { /* DigitalTwinOut | null */ },
  "health_score": 85,
  "active_alert_count": 3,
  "total_maintenance_cost": 680.0,
  "next_maintenance_items": [
    {
      "item_name": "刹车片检查",
      "category": "刹车",
      "priority": "high",
      "status": "overdue",
      "next_due_km": 10500,
      "next_due_date": null
    }
  ]
}
```

---

### 3.3 生命周期事件

#### GET `/api/vehicle/{vehicle_id}/lifecycle`
返回生命周期事件时间线。

查询参数：
| 参数 | 类型 | 说明 |
|------|------|------|
| `event_type` | string (可选) | 按事件类型筛选：purchase/maintenance/repair/accident/insurance/inspection/transfer/other |

响应 `200`：
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "event_type": "purchase",
      "title": "车辆购入",
      "description": "特斯拉上海体验中心购入",
      "event_date": "2024-03-15",
      "mileage": 0,
      "cost": 263900.0,
      "location": "上海",
      "severity": null,
      "created_at": "2024-03-15T10:00:00"
    }
  ],
  "total": 1
}
```

#### POST `/api/vehicle/{vehicle_id}/lifecycle`
创建生命周期事件。

请求体：
```json
{
  "event_type": "maintenance",
  "title": "首保",
  "description": "5,000公里首次保养",
  "event_date": "2024-06-10",
  "mileage": 5200,
  "cost": 0,
  "location": "特斯拉服务中心"
}
```
响应 `201`：返回 `LifecycleEventOut`。

#### DELETE `/api/vehicle/{vehicle_id}/lifecycle/{event_id}`
删除生命周期事件。响应 `204`。

---

### 3.4 健康快照

#### GET `/api/vehicle/{vehicle_id}/health`
返回健康快照历史。

查询参数：
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `limit` | int | 20 | 返回条数 (1-100) |

响应 `200`：
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "health_score": 85,
      "mileage": 12800,
      "engine_score": 88,
      "brake_score": 82,
      "tire_score": 78,
      "battery_score": 84,
      "body_score": 90,
      "electronics_score": 88,
      "summary": "刹车片和轮胎需重点关注",
      "source": "obd",
      "snapshot_time": "2025-01-20T08:00:00",
      "items": [
        {
          "id": 1,
          "snapshot_id": 1,
          "category": "brake",
          "item_name": "刹车片",
          "level": "warning",
          "score": 60,
          "detail": "剩余约5,000km",
          "recommendation": "尽快更换刹车片"
        }
      ]
    }
  ],
  "total": 1
}
```

#### GET `/api/vehicle/{vehicle_id}/health/latest`
返回最新一条健康快照（含明细项）。无数据时返回 `null`。

#### POST `/api/vehicle/{vehicle_id}/health`
创建健康快照（可同时写入明细项）。

请求体：
```json
{
  "health_score": 85,
  "mileage": 12800,
  "engine_score": 88,
  "brake_score": 82,
  "tire_score": 78,
  "battery_score": 84,
  "body_score": 90,
  "electronics_score": 88,
  "summary": "刹车片和轮胎需重点关注",
  "source": "obd",
  "items": [
    {
      "category": "brake",
      "item_name": "刹车片",
      "level": "warning",
      "score": 60,
      "detail": "剩余约5,000km",
      "recommendation": "尽快更换刹车片"
    }
  ]
}
```
响应 `201`：返回 `HealthSnapshotOut`。

#### DELETE `/api/vehicle/{vehicle_id}/health/{snapshot_id}`
删除健康快照。响应 `204`。

---

### 3.5 保养记录与计划

#### GET `/api/vehicle/{vehicle_id}/maintenance/records`
返回保养记录列表。

查询参数：`limit` (int, 默认50, 1-200)

响应 `200`：
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "maintenance_type": "routine",
      "category": "常规",
      "title": "首保",
      "description": "5,000公里首次保养",
      "maintenance_date": "2024-06-10",
      "mileage": 5200,
      "cost": 0.0,
      "service_provider": "特斯拉服务中心",
      "next_mileage": null,
      "next_date": null,
      "parts": ["机油滤芯", "空调滤芯"],
      "created_at": "2024-06-10T14:00:00"
    }
  ],
  "total": 1
}
```

#### POST `/api/vehicle/{vehicle_id}/maintenance/records`
创建保养记录。响应 `201`。

#### DELETE `/api/vehicle/{vehicle_id}/maintenance/records/{record_id}`
删除保养记录。响应 `204`。

#### GET `/api/vehicle/{vehicle_id}/maintenance/schedules`
返回保养计划列表（系统自动计算到期状态）。

响应 `200`：
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "item_name": "机油更换",
      "category": "发动机",
      "interval_km": 10000,
      "interval_days": 365,
      "last_mileage": 5200,
      "last_date": "2024-06-10",
      "next_due_km": 15200,
      "next_due_date": "2025-06-10",
      "status": "pending",
      "priority": "medium",
      "notes": null
    }
  ],
  "total": 1
}
```

**状态说明**：`status` 字段由系统自动计算：
- `overdue` — 已逾期（里程或日期超过到期值）
- `due` — 即将到期（里程差≤500km 或日期差≤7天）
- `pending` — 正常

#### POST `/api/vehicle/{vehicle_id}/maintenance/schedules`
创建保养计划。响应 `201`。

#### DELETE `/api/vehicle/{vehicle_id}/maintenance/schedules/{schedule_id}`
删除保养计划。响应 `204`。

---

### 3.6 驾驶行为

#### GET `/api/vehicle/{vehicle_id}/driving-behavior`
返回近期驾驶行为记录。

查询参数：`days` (int, 默认30, 1-365)

响应 `200`：
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "record_date": "2025-01-20",
      "trip_count": 4,
      "total_distance": 45.2,
      "total_duration": 3200,
      "avg_speed": 50.8,
      "max_speed": 95.0,
      "safety_score": 92,
      "eco_score": 88,
      "harsh_acceleration_count": 1,
      "harsh_braking_count": 2,
      "sharp_turn_count": 0,
      "overspeed_count": 0,
      "fuel_consumption": 6.8,
      "night_driving_ratio": 0.1,
      "created_at": "2025-01-20T23:00:00"
    }
  ],
  "total": 1
}
```

#### GET `/api/vehicle/{vehicle_id}/driving-behavior/summary`
返回驾驶行为汇总统计。

查询参数：`days` (int, 默认30, 1-365)

响应 `200`：
```json
{
  "vehicle_id": 1,
  "period_days": 30,
  "total_trips": 96,
  "total_distance": 1080.5,
  "total_duration": 76800,
  "avg_safety_score": 91.2,
  "avg_eco_score": 88.5,
  "total_harsh_events": 18,
  "total_fuel": 162.0
}
```

#### POST `/api/vehicle/{vehicle_id}/driving-behavior`
创建驾驶行为记录。响应 `201`。

#### DELETE `/api/vehicle/{vehicle_id}/driving-behavior/{behavior_id}`
删除驾驶行为记录。响应 `204`。

---

### 3.7 告警

#### GET `/api/vehicle/{vehicle_id}/alerts`
返回告警列表。

查询参数：
| 参数 | 类型 | 说明 |
|------|------|------|
| `status` | string (可选) | active/acknowledged/resolved |
| `level` | string (可选) | critical/warning/info |

响应 `200`：
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "level": "warning",
      "category": "刹车片",
      "title": "刹车片即将到达更换周期",
      "detail": "当前里程12,800km，建议更换里程10,500km",
      "recommendation": "预约特斯拉服务中心更换刹车片",
      "status": "active",
      "triggered_at": "2025-01-20T08:00:00",
      "acknowledged_at": null,
      "resolved_at": null,
      "created_at": "2025-01-20T08:00:00"
    }
  ],
  "total": 1
}
```

#### POST `/api/vehicle/{vehicle_id}/alerts`
创建告警。响应 `201`。

#### PATCH `/api/vehicle/{vehicle_id}/alerts/{alert_id}`
更新告警状态（确认/解决）。

请求体：
```json
{ "status": "acknowledged" }
```
响应 `200`：返回更新后的 `AlertOut`。

#### DELETE `/api/vehicle/{vehicle_id}/alerts/{alert_id}`
删除告警。响应 `204`。

---

### 3.8 所有权记录

#### GET `/api/vehicle/{vehicle_id}/ownership`
返回所有权变更历史。

响应 `200`：
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "owner_name": "张三",
      "transfer_type": "purchase",
      "start_date": "2024-03-15",
      "end_date": null,
      "purchase_price": 263900.0,
      "sale_price": null,
      "mileage_at_transfer": 0,
      "notes": "新车购入",
      "created_at": "2024-03-15T10:00:00"
    }
  ],
  "total": 1
}
```

#### POST `/api/vehicle/{vehicle_id}/ownership`
创建所有权记录。响应 `201`。

#### DELETE `/api/vehicle/{vehicle_id}/ownership/{record_id}`
删除所有权记录。响应 `204`。

---

### 3.9 数字孪生

#### GET `/api/vehicle/{vehicle_id}/digital-twin`
返回数字孪生模型信息。无数据时返回 `null`。

响应 `200`：
```json
{
  "id": 1,
  "vehicle_id": 1,
  "model_version": "v2.1",
  "model_url": "twin://tesla/model-y/001",
  "sync_status": "synced",
  "sync_frequency": "realtime",
  "last_sync_at": "2025-01-20T08:00:00",
  "telemetry": {
    "battery_level": 78,
    "tire_pressure_fl": 2.3,
    "tire_pressure_fr": 2.3,
    "tire_pressure_rl": 2.2,
    "tire_pressure_rr": 2.2,
    "cabin_temp": 22
  },
  "config": {
    "regen_level": "standard",
    "autopilot_enabled": true
  },
  "notes": null,
  "created_at": "2024-03-15T10:00:00",
  "updated_at": "2025-01-20T08:00:00"
}
```

#### POST `/api/vehicle/{vehicle_id}/digital-twin`
创建数字孪生模型（每辆车仅允许一个）。

请求体：
```json
{
  "model_version": "v2.1",
  "model_url": "twin://tesla/model-y/001",
  "sync_frequency": "realtime",
  "telemetry": {},
  "config": {}
}
```
响应 `201`：返回 `DigitalTwinOut`。
响应 `409`：`{ "detail": "Digital twin already exists for this vehicle" }`

#### PATCH `/api/vehicle/{vehicle_id}/digital-twin`
更新数字孪生配置。

#### POST `/api/vehicle/{vehicle_id}/digital-twin/telemetry`
推送遥测数据，更新孪生模型。

请求体：`{ "battery_level": 80, "tire_pressure_fl": 2.3 }`

响应 `200`：返回更新后的 `DigitalTwinOut`。

#### DELETE `/api/vehicle/{vehicle_id}/digital-twin`
删除数字孪生模型。响应 `204`。

---

### 3.10 传感器数据（IoT 遥测） `/api/vehicle/{vehicle_id}/sensors`

高频时序遥测数据，对应 `vehicle_sensor_data` 表。生产环境基于 TimescaleDB hypertable 分区。

#### GET `/api/vehicle/{vehicle_id}/sensors`
返回传感器读数列表。

查询参数：
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `sensor_type` | string (可选) | - | 按传感器类型筛选 |
| `limit` | int | 200 | 返回条数 (1-2000) |

响应 `200`：
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "sensor_type": "engine_temp",
      "sensor_value": 92.5,
      "unit": "℃",
      "meta": { "position": "cylinder_1" },
      "created_at": "2026-01-20T08:00:00"
    }
  ],
  "total": 1
}
```

#### GET `/api/vehicle/{vehicle_id}/sensors/types`
返回该车辆出现过的传感器类型列表。

响应 `200`：
```json
{ "vehicle_id": 1, "sensor_types": ["engine_temp", "battery_voltage", "tire_pressure"] }
```

#### GET `/api/vehicle/{vehicle_id}/sensors/series`
返回指定传感器类型的时间序列（用于图表）。

查询参数：
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `sensor_type` | string (必填) | - | 传感器类型 |
| `hours` | int | 24 | 时间窗口(小时, 1-720) |

响应 `200`：
```json
{
  "sensor_type": "engine_temp",
  "unit": "℃",
  "points": [
    { "timestamp": "2026-01-20T08:00:00", "value": 90.0 },
    { "timestamp": "2026-01-20T09:00:00", "value": 92.5 }
  ]
}
```

#### POST `/api/vehicle/{vehicle_id}/sensors`
创建单条传感器读数。响应 `201`，返回 `SensorDataOut`。

请求体：
```json
{ "sensor_type": "engine_temp", "sensor_value": 92.5, "unit": "℃", "meta": {} }
```

#### POST `/api/vehicle/{vehicle_id}/sensors/batch`
批量写入传感器读数。响应 `201`，返回 `SensorDataList`。

请求体：
```json
{
  "readings": [
    { "sensor_type": "engine_temp", "sensor_value": 92.5, "unit": "℃" },
    { "sensor_type": "battery_voltage", "sensor_value": 398.0, "unit": "V" }
  ]
}
```

---

### 3.11 行驶生命周期 `/api/vehicle/{vehicle_id}/trips`

记录车辆每一次旅程，对应 `vehicle_trips` 表。

#### GET `/api/vehicle/{vehicle_id}/trips`
返回行程列表。

查询参数：`limit` (int, 默认50, 1-500)

响应 `200`：
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "start_time": "2026-01-20T08:00:00",
      "end_time": "2026-01-20T09:30:00",
      "distance": 45.2,
      "average_speed": 50.8,
      "max_speed": 95.0,
      "energy_consumption": 3.2,
      "road_condition": "highway",
      "weather": "sunny",
      "harsh_acceleration_count": 1,
      "harsh_braking_count": 2,
      "overspeed_count": 0,
      "start_location": { "lat": 31.23, "lng": 121.47 },
      "end_location": { "lat": 31.30, "lng": 121.50 },
      "notes": null,
      "driver_id": 1,
      "created_at": "2026-01-20T09:30:00"
    }
  ],
  "total": 1
}
```

#### GET `/api/vehicle/{vehicle_id}/trips/summary`
返回指定时间窗口内的行程汇总统计。

查询参数：`days` (int, 默认30, 1-365)

响应 `200`：
```json
{
  "trip_count": 42,
  "total_distance": 980.5,
  "total_duration_hours": 28.5,
  "total_energy": 68.2,
  "avg_speed": 52.3,
  "harsh_events": 12,
  "first_trip_time": "2025-12-21T08:00:00",
  "last_trip_time": "2026-01-20T18:00:00"
}
```

#### POST `/api/vehicle/{vehicle_id}/trips`
创建行程记录。响应 `201`，返回 `TripOut`。

请求体：
```json
{
  "start_time": "2026-01-20T08:00:00",
  "end_time": "2026-01-20T09:30:00",
  "distance": 45.2,
  "average_speed": 50.8,
  "max_speed": 95.0,
  "energy_consumption": 3.2,
  "road_condition": "highway"
}
```

#### DELETE `/api/vehicle/{vehicle_id}/trips/{trip_id}`
删除行程记录。响应 `204`。

---

### 3.12 故障历史档案 `/api/vehicle/{vehicle_id}/faults`

车辆疾病史，对应 `vehicle_fault_logs` 表。

#### GET `/api/vehicle/{vehicle_id}/faults`
返回故障记录列表。

查询参数：
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `repair_status` | string (可选) | - | 按修复状态筛选 |
| `limit` | int | 100 | 返回条数 (1-500) |

响应 `200`：
```json
{
  "items": [
    {
      "id": 1,
      "vehicle_id": 1,
      "fault_code": "P0420",
      "fault_level": "medium",
      "description": "三元催化效率低",
      "system": "exhaust",
      "repair_status": "resolved",
      "mileage": 12000,
      "occur_time": "2025-12-15T10:00:00",
      "resolved_time": "2025-12-18T14:00:00",
      "maintenance_record_id": 3,
      "created_at": "2025-12-15T10:00:00"
    }
  ],
  "total": 1
}
```

#### POST `/api/vehicle/{vehicle_id}/faults`
创建故障记录。响应 `201`，返回 `FaultLogOut`。

请求体：
```json
{
  "fault_code": "P0420",
  "fault_level": "medium",
  "description": "三元催化效率低",
  "system": "exhaust",
  "repair_status": "active",
  "mileage": 12000,
  "occur_time": "2025-12-15T10:00:00"
}
```

#### PATCH `/api/vehicle/{vehicle_id}/faults/{fault_id}`
更新故障记录（如标记为已修复）。响应 `200`，返回 `FaultLogOut`。

请求体：
```json
{ "repair_status": "resolved", "resolved_time": "2025-12-18T14:00:00" }
```

#### DELETE `/api/vehicle/{vehicle_id}/faults/{fault_id}`
删除故障记录。响应 `204`。

---

### 3.13 实时数字状态 `/api/vehicle/{vehicle_id}/digital-state`

车辆当前快照状态，对应 `vehicle_digital_states` 表。每辆车最多一条记录。

#### GET `/api/vehicle/{vehicle_id}/digital-state`
返回车辆当前数字状态。无数据时返回 `null`。

响应 `200`：
```json
{
  "id": 1,
  "vehicle_id": 1,
  "engine_health": 88.0,
  "battery_health": 92.0,
  "brake_health": 75.0,
  "tire_health": 80.0,
  "body_health": 95.0,
  "electronics_health": 90.0,
  "overall_score": 86.5,
  "status": "GOOD",
  "temperature": 92.0,
  "mileage": 12800,
  "fuel_level": 78.0,
  "location": { "lat": 31.23, "lng": 121.47 },
  "updated_at": "2026-01-20T08:00:00",
  "created_at": "2026-01-15T10:00:00"
}
```

#### PUT `/api/vehicle/{vehicle_id}/digital-state`
整体写入/替换数字状态（upsert）。响应 `200`，返回 `DigitalStateOut`。

请求体：
```json
{
  "engine_health": 88.0,
  "battery_health": 92.0,
  "brake_health": 75.0,
  "overall_score": 86.5,
  "status": "GOOD",
  "temperature": 92.0,
  "mileage": 12800,
  "fuel_level": 78.0
}
```

#### PATCH `/api/vehicle/{vehicle_id}/digital-state`
部分更新数字状态（仅传需要更新的字段）。响应 `200`，返回 `DigitalStateOut`。

请求体示例：`{ "fuel_level": 65.0, "mileage": 13050 }`

#### DELETE `/api/vehicle/{vehicle_id}/digital-state`
删除数字状态。响应 `204`。

---

### 3.14 车辆数字生命档案 `/api/vehicle/{vehicle_id}/life`

**旗舰接口** — 返回车辆数字孪生的核心叙事视图，聚合身份、健康、里程、寿命预测、生命事件时间线、AI 预测与建议。

#### GET `/api/vehicle/{vehicle_id}/life`
查询车辆数字生命档案。

响应 `200`：
```json
{
  "identity": {
    "vehicle_id": 1,
    "digital_identity": "VX-2026-00001",
    "name": "Model Y",
    "brand": "Tesla",
    "model": "Model Y",
    "year": 2024,
    "vin": "LSJW32E78PD000017",
    "energy_type": "electric",
    "color": "珍珠白",
    "nickname": "小白",
    "avatar_url": null
  },
  "health_score": 86,
  "health_grade": "excellent",
  "health_grade_label": "优秀",
  "status": "GOOD",
  "status_label": "健康",
  "age_years": 1.8,
  "age_label": "1年10个月",
  "mileage": 12800,
  "mileage_label": "12,800 km",
  "predicted_lifespan_years": 12.0,
  "predicted_remaining_years": 10.2,
  "predicted_lifespan_label": "预计还能陪伴 10.2 年",
  "today_temperature": 22.0,
  "today_fuel_level": 78.0,
  "today_location": { "lat": 31.23, "lng": 121.47 },
  "engine_health": 88.0,
  "battery_health": 92.0,
  "brake_health": 75.0,
  "tire_health": 80.0,
  "health_breakdown": {
    "engine": 88.0,
    "battery": 92.0,
    "chassis": 77.5,
    "driving": 85.0,
    "maintenance": 90.0,
    "engine_contribution": 26.4,
    "battery_contribution": 23.0,
    "chassis_contribution": 11.6,
    "driving_contribution": 12.8,
    "maintenance_contribution": 13.5
  },
  "life_events": [
    {
      "date": "2024-03-15",
      "event_type": "purchase",
      "title": "车辆购入",
      "description": "特斯拉上海体验中心购入",
      "mileage": 0,
      "cost": 263900.0,
      "icon": "car"
    },
    {
      "date": "2024-06-10",
      "event_type": "maintenance",
      "title": "首保",
      "description": "5,000公里首次保养",
      "mileage": 5200,
      "cost": 0.0,
      "icon": "tool"
    }
  ],
  "predictions": [
    {
      "component": "刹车片",
      "current_health": 75.0,
      "predicted_failure_date": "2026-04-15",
      "risk_level": "medium",
      "reason": "刹车片磨损已达75%，按当前驾驶频率预计8000公里后超过阈值",
      "suggestion": "未来5000公里建议检查刹车片"
    }
  ],
  "ai_suggestions": [
    "刹车系统需要维护",
    "轮胎气压偏低，建议补充至2.5bar"
  ],
  "total_trips": 142,
  "total_maintenance_cost": 680.0,
  "fault_count": 2,
  "active_fault_count": 0,
  "ai_doctor_enabled": false,
  "personality": null
}
```

> `ai_doctor_enabled` 与 `personality` 为 TASK008 AI 车辆医生 + 车辆人格化预留扩展字段。

---

### 3.15 健康评分 (VHS) `/api/vehicle/{vehicle_id}/health-score`

计算车辆健康评分（Vehicle Health Score），基于加权模型：
`VHS = 0.30·发动机 + 0.25·电池 + 0.15·底盘 + 0.15·驾驶习惯 + 0.15·维修记录`

#### GET `/api/vehicle/{vehicle_id}/health-score`
计算并返回车辆健康评分。

响应 `200`：
```json
{
  "vehicle_id": 1,
  "score": 86.5,
  "grade": "excellent",
  "grade_label": "优秀",
  "breakdown": {
    "engine": 88.0,
    "battery": 92.0,
    "chassis": 77.5,
    "driving": 85.0,
    "maintenance": 90.0,
    "engine_contribution": 26.4,
    "battery_contribution": 23.0,
    "chassis_contribution": 11.6,
    "driving_contribution": 12.8,
    "maintenance_contribution": 13.5
  },
  "weights": {
    "engine": 0.30,
    "battery": 0.25,
    "chassis": 0.15,
    "driving": 0.15,
    "maintenance": 0.15
  },
  "computed_at": "2026-01-20T08:00:00"
}
```

**评级标准**：
| 分数区间 | grade | grade_label |
|----------|-------|-------------|
| 95-100 | golden | 黄金车况 |
| 80-95 | excellent | 优秀 |
| 60-80 | fair | 一般 |
| <60 | risk | 风险车辆 |

---

### 3.16 模拟数据生成器 `/api/vehicle/{vehicle_id}/simulate`

数字孪生模拟器 — 生成逼真的传感器、行程、故障数据并刷新实时数字状态，用于开发演示与测试。

#### POST `/api/vehicle/{vehicle_id}/simulate`
生成模拟数据（传感器/行程/故障）并刷新实时数字状态。

请求体：
```json
{
  "vehicle_id": 1,
  "sensor_points": 24,
  "trip_count": 5,
  "fault_count": 0,
  "days": 7,
  "update_digital_state": true
}
```

响应 `200`：
```json
{
  "vehicle_id": 1,
  "sensor_data_created": 24,
  "trips_created": 5,
  "faults_created": 0,
  "digital_state_updated": true,
  "message": "已生成 24 条传感器数据、5 条行程数据，并刷新实时数字状态"
}
```

#### POST `/api/vehicle/{vehicle_id}/simulate/quick`
快速生成模拟数据（无需请求体，全部走 query 参数）。

查询参数：
| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `sensor_points` | int | 24 | 传感器数据点数 (1-500) |
| `trip_count` | int | 5 | 行程数 (0-50) |
| `fault_count` | int | 0 | 故障数 (0-10) |
| `days` | int | 7 | 数据时间跨度(天, 1-90) |

响应 `200`：返回 `SimulationResult`（同上）。

---

## 4. Agent 接口 `/api/agent`

### POST `/api/agent/chat`
与 AI 守护 Agent 对话。

请求体：
```json
{ "user": "test", "message": "我的车需要保养吗" }
```
响应 `200`：
```json
{ "answer": "string", "agent_status": "active" }
```

> Agent 可调用以下工具获取数据：
> - `get_vehicle_info` — 车辆基本信息
> - `get_health_score` — 健康指数与风险项
> - `get_maintenance_plan` — 保养计划建议
> - `get_driving_behavior` — 驾驶行为分析
> - `get_lifecycle_timeline` — 生命周期时间线
> - `get_alerts` — 活跃告警列表
> - `get_vehicle_life` — 数字生命档案（旗舰聚合视图）
> - `get_vhs_score` — VHS 加权健康评分与分项贡献
> - `get_sensor_data` — 传感器时序遥测数据
> - `get_trips` — 行驶生命周期记录
> - `get_faults` — 故障历史档案

---

## 5. 知识库接口 `/api/knowledge`

RAG（检索增强生成）汽车知识库。支持语义检索、文档导入、索引重建。

### POST `/api/knowledge/search`
混合检索（向量相似度 + BM25 关键词），返回排序后的知识片段。

请求体：
```json
{ "query": "机油多久换一次", "top_k": 5 }
```

响应 `200`：
```json
{
  "query": "机油多久换一次",
  "results": [
    {
      "title": "汽车保养知识手册",
      "heading": "保养周期",
      "category": "maintenance",
      "source": "maintenance.md",
      "score": 0.85,
      "backend": "vector",
      "text": "机油更换周期：矿物油 5000km/6个月…"
    }
  ],
  "count": 5,
  "context": "【检索查询】…\n【知识库检索结果】…",
  "stats": {
    "chunk_count": 66,
    "backend": "inmemory",
    "embedder": "hash",
    "ready": true
  }
}
```

### POST `/api/knowledge/ingest`
导入单篇文本文档到知识库（自动分块、嵌入、索引）。

请求体：
```json
{
  "title": "冬季轮胎使用指南",
  "category": "tire_brake",
  "content": "冬季轮胎应在气温低于7摄氏度时更换…",
  "source": "web-ui"
}
```

响应 `200`：
```json
{
  "title": "冬季轮胎使用指南",
  "chunks_added": 1,
  "total_chunks": 67,
  "message": "成功导入 1 个知识片段"
}
```

### GET `/api/knowledge/stats`
返回知识库状态。

响应 `200`：
```json
{
  "chunk_count": 66,
  "backend": "inmemory",
  "embedder": "hash",
  "docs_dir": ".../knowledge/docs",
  "ready": true
}
```

### POST `/api/knowledge/rebuild`
清空索引并从内置文档目录重新构建。

响应 `200`：
```json
{
  "chunks": 66,
  "message": "知识库已重建，共 66 个片段",
  "stats": { "chunk_count": 66, "backend": "inmemory", "ready": true }
}
```

> **知识类别**：`maintenance`(保养) `fault_diagnosis`(故障) `ev_battery`(新能源) `driving_tips`(驾驶) `tire_brake`(轮胎刹车) `insurance_law`(保险法规) `new_car_guide`(新车) `used_car`(二手车) `general`(通用)
>
> **优雅降级**：无 OpenAI API Key 时使用 Hash 嵌入；无 ChromaDB 时使用内存向量存储。系统始终可用。

---

## 6. 健康指数 `/api/health`

### GET `/api/health/overview`
返回系统健康概览。

响应 `200`：
```json
{ "health_score": 92, "agent_status": "active", "recent_alerts": [] }
```

---

## 7. 错误响应

所有接口在出错时返回统一格式：

```json
{ "detail": "错误描述信息" }
```

| HTTP 状态码 | 说明 |
|-------------|------|
| 400 | 请求参数校验失败 |
| 404 | 资源不存在 |
| 409 | 资源冲突（如重复创建数字孪生） |
| 422 | 请求体格式错误 |
| 500 | 服务器内部错误 |

---

## 8. 枚举值参考

| 字段 | 可选值 |
|------|--------|
| `fuel_type` | gasoline, diesel, electric, hybrid, plug_in_hybrid |
| `status` (车辆) | active, idle, sold, scrapped |
| `event_type` | purchase, maintenance, repair, accident, insurance, inspection, transfer, other |
| `maintenance_type` | routine, major, minor, repair, inspection, other |
| `alert.level` | critical, warning, info |
| `alert.status` | active, acknowledged, resolved |
| `schedule.status` | overdue, due, pending (系统自动计算) |
| `schedule.priority` | high, medium, low |
| `health_item.level` | good, warning, critical |
| `transfer_type` | purchase, sale, transfer, inheritance, gift, other |
| `sync_status` (孪生) | synced, syncing, error, pending |
| `digital_state.status` | GOOD, WARNING, DANGER, END_OF_LIFE |
| `fault_level` | low, medium, high, critical |
| `fault.repair_status` | active, resolved |
| `health_grade` | golden, excellent, fair, risk |
| `prediction.risk_level` | low, medium, high |

---

## 9. 数据库表对照（TASK007）

| API 端点分组 | 数据库表 | 说明 |
|--------------|----------|------|
| 3.1 车辆 CRUD | `vehicles` | 车辆基础身份 |
| 3.2 档案聚合 | (多表聚合) | 完整数字生命档案 |
| 3.3 生命周期事件 | `lifecycle_events` | 成长记录时间线 |
| 3.4 健康快照 | `health_snapshots` + `health_items` | 健康状态快照 |
| 3.5 保养记录与计划 | `maintenance_records` + `maintenance_schedules` | 维修病历 |
| 3.6 驾驶行为 | `driving_behaviors` | 驾驶行为画像 |
| 3.7 告警 | `alerts` | 风险告警 |
| 3.8 所有权记录 | `ownership_records` | 车辆数字遗产 |
| 3.9 数字孪生 | `digital_twins` | 孪生模型元数据 |
| 3.10 传感器数据 | `vehicle_sensor_data` (TimescaleDB hypertable) | IoT 遥测时序 |
| 3.11 行程 | `vehicle_trips` (TimescaleDB hypertable) | 行驶生命周期 |
| 3.12 故障档案 | `vehicle_fault_logs` | 车辆疾病史 |
| 3.13 数字状态 | `vehicle_digital_states` | 实时状态快照 |
| 3.14 数字生命档案 | (多表聚合) | 旗舰叙事视图 |
| 3.15 健康评分 | (实时计算) | VHS 加权模型 |
| 3.16 模拟器 | (写入 3.10/3.11/3.12/3.13) | 数据生成器 |
