# CarSoul OS Vehicle Schema 规范

> 版本：v1.0.0 · 2026-08-03
> 对应代码：`vehicle_protocol/vehicle_schema/`
> 独立包名：`carsoul-schema`

---

## 1. 概述

Vehicle Schema 是 CarSoul OS 的全局数据契约——所有模块（模拟器、数字孪生、Agent 运行时、知识库）之间的数据交换必须遵循本规范。

设计原则：
- **独立于 ORM**：Pydantic v2 模型，不绑定 SQLAlchemy 或任何数据库
- **可序列化**：所有模型支持 JSON 序列化 / 反序列化
- **带约束**：字段级约束（单位、范围、枚举）内嵌于模型定义
- **语义版本**：semver 管理，消费者可检测兼容性

---

## 2. 版本规则

| 变更类型 | semver 位 | 示例 |
|---|---|---|
| 字段删除或类型变更 | MAJOR | 1.0 → 2.0 |
| 向后兼容的字段新增（带默认值） | MINOR | 1.0 → 1.1 |
| 文档 / 约束细化 | PATCH | 1.0 → 1.0.1 |

消费者通过 `is_compatible(version_str)` 检查主版本兼容性。

---

## 3. 模型定义

### 3.1 VehicleIdentity（车辆身份）

车辆的唯一身份标识，是所有其他模型的根引用。

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `vin` | str | ✅ | 11-17 字符 | 车辆识别码（ISO 3779） |
| `brand` | str | ✅ | 1-64 字符 | 品牌 |
| `model` | str | ✅ | 1-64 字符 | 车型 |
| `year` | int | ✅ | 1900-2100 | 年款 |
| `fuel_type` | enum | ✅ | 见下 | 能源类型 |
| `battery_capacity` | float? | 条件 | ≥0 | 电池容量（kWh），EV/混动必填 |
| `engine_type` | str? | ❌ | ≤64 字符 | 发动机/电机型号 |
| `displacement` | float? | ❌ | ≥0 | 排量（L），燃油车 |

**fuel_type 枚举：** `gasoline` | `diesel` | `hybrid` | `plug_in_hybrid` | `electric`

**校验规则：** 当 `fuel_type` 为 `electric`/`hybrid`/`plug_in_hybrid` 时，`battery_capacity` 必填。

---

### 3.2 BatteryState（电池状态）

电池健康快照，模拟器发射、数字孪生消费。

| 字段 | 类型 | 必填 | 约束 | 单位 | 说明 |
|---|---|---|---|---|---|
| `soh` | float | ✅ | 0-100 | % | 电池健康度，100=全新 |
| `temperature` | float | ✅ | -40~120 | °C | 电池包温度 |
| `charge_cycles` | int | ✅ | ≥0 | 次 | 累计充放电循环数 |
| `fast_charge_ratio` | float | ✅ | 0-1 | 比例 | 快充占比 |
| `soc` | float? | ❌ | 0-100 | % | 当前电量 |
| `status` | enum | ❌ | 见下 | — | 派生健康状态 |

**status 枚举（ComponentStatus）：** `normal` | `degrading` | `warning` | `critical`

**模拟逻辑：**
- 新车 soh = 100，每 100 次循环衰减约 0.5-1.0%
- 快充比例 > 0.7 时衰减速率 ×1.5
- 温度 > 45°C 持续时进入 `warning` 状态

---

### 3.3 MotorState（电机/发动机状态）

| 字段 | 类型 | 必填 | 约束 | 单位 | 说明 |
|---|---|---|---|---|---|
| `efficiency` | float | ✅ | 0-1 | 比率 | 当前效率，1.0=设计效率 |
| `wear` | float | ✅ | 0-1 | 比率 | 磨损程度，0=全新，1=报废 |
| `temperature` | float? | ❌ | -40~200 | °C | 电机/发动机温度 |
| `status` | enum | ❌ | ComponentStatus | — | 派生健康状态 |

**模拟逻辑：**
- 磨损随里程线性增长，激烈驾驶加速磨损
- 效率 = 设计效率 × (1 - wear × 0.3)
- wear > 0.7 进入 `warning`，> 0.9 进入 `critical`

---

### 3.4 ChassisState（底盘状态）

| 字段 | 类型 | 必填 | 约束 | 单位 | 说明 |
|---|---|---|---|---|---|
| `brake_wear` | float | ✅ | 0-1 | 比率 | 刹车片磨损，0=新，1=需更换 |
| `tire_wear` | float | ✅ | 0-1 | 比率 | 轮胎磨损，0=满花纹，1=光头 |
| `suspension_health` | float | ✅ | 0-100 | 分 | 悬挂健康度 |
| `tire_pressure` | float? | ❌ | 0-5 | bar | 平均胎压 |
| `status` | enum | ❌ | ComponentStatus | — | 派生健康状态 |

**模拟逻辑：**
- 刹车片磨损：每 1 万 km 约 +0.1，激烈驾驶 ×1.5
- 轮胎磨损：每 2 万 km 约 +0.15
- brake_wear > 0.8 或 tire_wear > 0.85 进入 `critical`

---

### 3.5 DrivingProfile（驾驶画像）

| 字段 | 类型 | 必填 | 约束 | 单位 | 说明 |
|---|---|---|---|---|---|
| `style` | enum | ✅ | 见下 | — | 驾驶风格分类 |
| `safety_score` | float | ✅ | 0-100 | 分 | 安全评分 |
| `eco_score` | float | ✅ | 0-100 | 分 | 节能评分 |
| `harsh_event_count` | int | ❌ | ≥0，默认0 | 次 | 激烈事件数 |
| `avg_speed` | float? | ❌ | ≥0 | km/h | 平均车速 |

**style 枚举（DrivingStyle）：** `eco` | `balanced` | `aggressive` | `sporty`

---

### 3.6 ImpactRef（影响引用）

记忆引擎的因果链接——将生命周期事件关联到对车辆部件的量化影响。

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `target` | str | ✅ | — | 受影响部件/指标（如 `battery_stress`） |
| `delta` | float | ✅ | — | 影响幅度（如 +0.3 应力，-5 健康） |
| `confidence` | float | ❌ | 0-1，默认0.8 | 影响评估置信度 |

---

### 3.7 LifecycleEvent（生命周期事件）

车辆生命时间线上的一个节点。生命周期事件是原始日志，记忆引擎在其上叠加解释层。

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `event_type` | enum | ✅ | 见下 | 事件类型 |
| `date` | date | ✅ | — | 发生日期 |
| `mileage` | float | ✅ | ≥0 | 里程（km） |
| `title` | str | ✅ | 1-128 字符 | 事件标题 |
| `description` | str? | ❌ | — | 详细描述 |
| `severity` | enum? | ❌ | info/minor/moderate/major/critical | 严重度 |
| `cost` | float? | ❌ | ≥0 | 费用（元） |
| `impact` | ImpactRef? | ❌ | — | 记忆引擎影响链接 |

**event_type 枚举（EventType）：** `purchase` | `transfer` | `accident` | `repair` | `maintenance` | `inspection` | `insurance` | `registration` | `fault` | `custom`

---

### 3.8 TelemetryFrame（遥测帧）

**模拟器的原子发射单元。** 每个 TelemetryFrame 是一个完整的时刻快照，数据流：模拟器 → 数字孪生 → Agent 运行时。

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `ts` | datetime | ✅ | — | 帧时间戳（UTC） |
| `vin` | str | ✅ | 11-17 字符 | 车辆识别码 |
| `battery` | BatteryState? | ❌ | — | 电池状态（EV/混动） |
| `motor` | MotorState | ✅ | — | 电机/发动机状态 |
| `chassis` | ChassisState | ✅ | — | 底盘状态 |
| `driving` | DrivingProfile | ✅ | — | 驾驶画像 |
| `mileage` | float | ✅ | ≥0 | 里程（km） |
| `ambient_temp` | float? | ❌ | -50~60 | 环境温度（°C） |

---

## 4. 适用边界

### 4.1 模拟数据声明

本规范定义的所有模型用于**虚拟车模拟器**产生的数据，不代表真实车辆遥测。所有演示页面须标注"演示模式·模拟数据"。

### 4.2 不替代专业判断

基于本规范数据生成的健康评分、故障诊断、估值区间均为参考信息，不替代专业技师判断。

### 4.3 守护非控制

本规范覆盖的数据均为**只读感知层**数据。任何控制类能力（制动、转向、加速）不在本规范范围内。

---

## 5. 数据来源与脱敏

| 数据来源 | 说明 |
|---|---|
| 虚拟车模拟器 | 基于车型画像（performance_ev / family_ev / hybrid）的参数化模拟 |
| 退化曲线 | 基于公开行业数据的电池/部件衰减模型，非特定厂商数据 |
| 驾驶行为 | 基于驾驶风格枚举的行为模型，非真实用户数据 |

本规范不涉及真实车辆数据接入。
