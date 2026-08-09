# CarSoul 全车传感器模拟数据建模方案 v1.0

> 作者：数匠（DataEngineer） · 团队：carsoul-datasim
> 状态：设计稿，待后端落地评审
> 适用对象：Guardian 后端工程师、carModel 仿真/建模工程师

---

## 0. 结论摘要（给赶时间的人）

1. **不要新造一套数据模型。** 本方案是既有三套契约的**可投影超集**：高频传感器落 `vehicle_sensor_data`（EAV），日级聚合投影成 `vehicle_state_history` 的 9 列喂 XGBoost，健康分投影成 `vehicle_health_snapshots` 的 6 个子分列。三层之间是**纯函数投影**，不是三份独立数据。
2. **共 8 个域 / 104 个信号**，每个信号带单位、量程、采样频率、噪声模型、所属健康分域。
3. **物理合理性靠 7 条守恒/耦合方程保证**，不是给每个字段独立加正态噪声——独立加噪是"假数据"最容易被一眼看穿的地方（SOC 掉了但里程没动、电流是 0 但电芯在发热）。
4. **健康分 = 8 域扣分制 → 投影到 Guardian 现有 6 列**，无需数据库迁移。
5. **what-if 走纯函数**：`simulate_snapshot(profile, overrides, seed) -> Snapshot`，不落库，同 seed 同输入必然同输出。
6. ⚠️ **发现 2 个既有数据质量缺陷**（DTC 码语义与 BEV 不符、seed 里程与需求描述不一致），见 §9.2，建议本次一并修掉。

---

## 1. 既有契约（硬约束，设计不得违反）

这些不是我的设计，是我从代码里读出来的**现状**。任何模拟数据方案如果打破它们，就会连带打断 SOH 预测链路。

### 1.1 XGBoost 特征契约 —— 最硬的约束

来源：`carModel/models/battery_health/features.py::extract_features()`

模型只吃 `vehicle_state_history` 的这 **9 个时序列**（滑窗 180 行）：

| 列名 | 说明 |
|---|---|
| `soh` | 健康度 %（特征里 /100 归一） |
| `soc` | 荷电状态 % |
| `temp` | **电芯**温度 ℃ |
| `ambient_temp` | 环境温度 ℃ |
| `mileage_km` | 累计里程 |
| `cycles` | 累计等效循环 |
| `fast_ratio` | 快充占比（NaN 时回填 0.3） |
| `hard_accel` | 急加速次数 |
| `hard_brake` | 急刹次数 |

加 **6 个 profile 静态特征**（`vehicle_profile`，one-hot 展开）：

| 字段 | 取值域（`_STATIC` 权威定义） |
|---|---|
| `capacity_kwh` | float |
| `chemistry` | `LFP` / `NMC` / `NCA` / `LMFP` |
| `climate` | `cold` / `temperate` / `hot` |
| `driving_style` | `gentle` / `moderate` / `aggressive` |
| `charge_style` | `slow` / `fast_mix` |
| `dod` | `shallow` / `deep` |

> **落地约束**：新增的 100 个传感器信号，**一个都不能进 XGBoost 输入**，否则特征维度对不上、模型直接报错。它们只能通过"聚合成上面 9 列"的方式影响预测。这是本方案 §2 分层的根本原因。

### 1.2 `t_index` / `age_days` 唯一来源

来源：`carModel/simulator/db.py::count_history()`

```
age_days = t_index = count_history(conn, vehicle_id)
         = SELECT COUNT(*) FROM vehicle_state_history
           WHERE vehicle_id=? AND soh IS NOT NULL
```

- ❌ 不得用 `cycles`（量纲不同）
- ❌ 不得用 `len(最近 N 行)`（被 LIMIT 截断成常数）
- 二者即历史 BC-06 缺陷，已于 2026-08-08 修复，**模拟器回填历史数据时必须保持每车每天恰好 1 行**，否则 `age_days` 会被灌水，SOH 预测系统性偏移。
- 索引 `idx_state_vid_soh(vehicle_id, soh)` 必须存在，否则该 COUNT 约 19ms 并摊到每次 `/world/predict`。

### 1.3 Guardian 存储契约

| 表 | 关键约束 |
|---|---|
| `vehicle_sensor_data` | EAV 结构：`sensor_type`(str) + `sensor_value`(float) + `unit` + `meta`(JSON)。**只能存标量**，多点信号（4 轮胎压、8 路电芯温度）靠 `meta` 区分位置 |
| `vehicle_health_snapshots` | 子分列**固定 6 个**：`engine_score` / `brake_score` / `tire_score` / `battery_score` / `body_score` / `electronics_score`。总分 `health_score` 为 0-100 整数 |
| `vehicle_health_items` | `category` ∈ `engine\|brake\|tire\|battery\|body\|electronics\|fluid\|other`；`level` ∈ `ok\|info\|warning\|critical` |
| `vehicle_fault_logs` | `fault_level` ∈ `low\|medium\|high\|critical`；`system` ∈ `engine\|transmission\|brake\|battery\|tire\|electronics\|body\|other`；`repair_status` ∈ `active\|diagnosing\|repairing\|resolved\|ignored` |
| `simulator/constants.py::DTC_CODES` | 权威 7 码：`P0301` `P0AA6` `P0CE0` `P1E00` `P0562` `C0123` `U0100`。**新增故障必须复用这 7 码**，否则 fleet / life_simulator 口径再次分裂 |

### 1.4 Demo 车基线（seed_data.py）

Tesla Model Y 2024 /「小白」/ VIN `LSJW32E78PD000017` / 沪A·D2024 / 电池 60.0 kWh / 里程 12800 / 购入 2024-03-15。
（团队描述的"12,692km / 健康分 84 / 5 次故障"与 seed 常量 12800 不一致——见 §9.2 数据质量问题 #2。）

---

## 2. 三层数据架构（本方案的骨架）

```
┌─ L0 原始传感器层 ───────────────────────────────────────────┐
│  104 个信号 · 采样率 0.001Hz ~ 100Hz                        │
│  落库: vehicle_sensor_data (EAV)  ← 只存"当前快照"+抽样      │
│  用途: 前端仪表盘实时展示、Agent 感知、异常注入               │
└──────────────────────┬──────────────────────────────────────┘
                       │  daily_aggregate()  纯函数投影
                       ▼
┌─ L1 日级状态层 ─────────────────────────────────────────────┐
│  9 列 + failure 标志 · 每车每天恰好 1 行 (t_index 依赖!)      │
│  落库: vehicle_state_history                                │
│  用途: XGBoost SOH 预测的唯一输入                            │
└──────────────────────┬──────────────────────────────────────┘
                       │  score_health()  纯函数投影
                       ▼
┌─ L2 健康与故障层 ───────────────────────────────────────────┐
│  8 域扣分 → 6 个子分列 + 总分 + 故障清单                     │
│  落库: vehicle_health_snapshots / _items / vehicle_fault_logs│
│  用途: 健康分仪表盘、风险预警、服务工单触发                    │
└─────────────────────────────────────────────────────────────┘
```

**关键设计决策：**

- **L0 不做全量时序落库。** 104 信号 × 10Hz × 86400s ≈ 9000 万点/车/天，SQLite 撑不住。L0 只落**当前快照**（每信号 1 行，upsert）+ **异常时刻抽样**。历史趋势由 L1 承担。
- **投影是纯函数。** `L0 → L1 → L2` 全部无副作用，这是 what-if 能"不落库预览"的前提：同一套函数，落库路径写 DB，预览路径直接返回。
- **L1 是 t_index 的地基。** 严禁为了"数据更丰富"给某天插 2 行 —— 会直接污染 `age_days`。

---

## 3. 全车传感器信号总表

**表头约定：**
- `sensor_type` = 落 `vehicle_sensor_data.sensor_type` 的字符串主键，全局唯一，`域前缀.信号名` 命名
- `Hz` = 典型采样频率（`d` = 每日 1 次，`evt` = 事件触发）
- `健康域` = 该信号参与哪个健康分域计算（见 §6），`—` 表示仅展示不计分
- `噪声` = 模拟时叠加的噪声模型，`N(0,σ)` 为高斯，`RW` 为随机游走
- **粗体**信号 = 参与 L1 投影（喂 XGBoost）或触发故障判定的关键信号

### 3.1 动力电池域 `bat.*` — 24 信号

| sensor_type | 物理含义 | 单位 | 合理范围 | Hz | 健康域 | 噪声 |
|---|---|---|---|---|---|---|
| `bat.pack_voltage` | 动力电池总压 | V | 240–450 | 10 | BAT | N(0,0.3) |
| `bat.pack_current` | 总电流（**+放电 / −充电**） | A | −600 – 400 | 10 | BAT | N(0,1.5) |
| `bat.pack_power` | 瞬时功率（派生 U×I） | kW | −250 – 250 | 10 | — | 派生 |
| `bat.cell_volt_min` | 单体最低电压 | V | 2.50–4.25 | 1 | BAT | N(0,0.002) |
| `bat.cell_volt_max` | 单体最高电压 | V | 2.50–4.25 | 1 | BAT | N(0,0.002) |
| `bat.cell_volt_avg` | 单体平均电压 | V | 2.50–4.25 | 1 | — | 派生 |
| **`bat.cell_volt_delta`** | **单体压差**（max−min，一致性核心指标） | mV | 0–500 | 1 | BAT | 派生 |
| `bat.cell_temp_[01..08]` | 8 路电芯温度（`meta.channel`） | ℃ | −30 – 65 | 1 | BAT/THM | N(0,0.4) |
| **`bat.cell_temp_max`** | **电芯最高温**（热失控判据） | ℃ | −30 – 65 | 1 | BAT | 派生 |
| `bat.cell_temp_min` | 电芯最低温 | ℃ | −30 – 65 | 1 | BAT | 派生 |
| **`bat.cell_temp_avg`** | **电芯均温** → L1 `temp` 列 | ℃ | −30 – 65 | 1 | BAT | 派生 |
| `bat.cell_temp_delta` | 温度极差（热管理均匀性） | ℃ | 0–25 | 1 | THM | 派生 |
| **`bat.soc`** | 荷电状态（真值） | % | 0–100 | 1 | BAT | RW+N(0,0.2) |
| `bat.soc_display` | 仪表显示 SOC（含缓冲区映射） | % | 0–100 | 1 | — | 派生 |
| **`bat.soh`** | 健康度（XGBoost 目标/输入） | % | 65–100 | d | BAT | 见 §4.1 |
| **`bat.internal_resistance`** | 包级直流内阻 DCIR | mΩ | 55–260 | d | BAT | N(0,1.5) |
| **`bat.insulation_resistance`** | 绝缘电阻（GB 要求 ≥500 Ω/V） | kΩ | 0–50000 | 0.1 | BAT | 对数 RW |
| `bat.balance_active` | 均衡是否工作 | bool | 0/1 | 0.1 | — | 规则 |
| `bat.balance_cell_count` | 正在均衡的单体数 | int | 0–106 | 0.1 | BAT | 规则 |
| **`bat.charge_cycles`** | 累计等效满充循环 | 次 | 0–3000 | d | BAT | 派生 |
| `bat.energy_throughput` | 累计能量吞吐 | kWh | 0–200000 | d | — | 派生 |
| `bat.max_charge_power_allow` | BMS 允许充电功率上限 | kW | 0–250 | 1 | BAT | 规则 |
| `bat.max_discharge_power_allow` | BMS 允许放电功率上限 | kW | 0–350 | 1 | BAT | 规则 |
| `bat.capacity_remain` | 剩余可用能量 | kWh | 0–120 | 1 | — | 派生 |

> **化学体系差异**（必须按 `profile.chemistry` 切换，否则 LFP 车出现 4.2V 单体就穿帮）：
> | chemistry | 单体下限 | 标称 | 单体上限 | OCV 平台特征 |
> |---|---|---|---|---|
> | LFP / LMFP | 2.50 V | 3.20 V | 3.65 V | 20–90% SOC **极平坦**（≈3.28V），SOC 估计难 |
> | NMC / NCA | 3.00 V | 3.70 V | 4.20 V | 单调倾斜，SOC 可由电压反推 |
>
> Demo 车「小白」为国产 Model Y 60 kWh，按 **LFP** 建模。

### 3.2 驱动电机域 `drv.*` — 13 信号

双电机四驱（`engine_type="双电机四驱"`），前后各一套，`meta.axle` ∈ `front`/`rear`。

| sensor_type | 物理含义 | 单位 | 合理范围 | Hz | 健康域 | 噪声 |
|---|---|---|---|---|---|---|
| `drv.motor_rpm_front` / `_rear` | 电机转速 | rpm | 0–18000 | 20 | DRV | N(0,15) |
| `drv.torque_front` / `_rear` | 输出扭矩（负=回收） | N·m | −450 – 450 | 20 | DRV | N(0,3) |
| **`drv.stator_temp_front` / `_rear`** | **定子绕组温度**（过温降功率） | ℃ | −30 – 180 | 1 | DRV | N(0,0.8) |
| **`drv.inverter_temp_front` / `_rear`** | **控制器/IGBT 温度** | ℃ | −30 – 125 | 1 | DRV | N(0,0.6) |
| `drv.phase_current_front` / `_rear` | 相电流有效值 | A(rms) | 0–800 | 20 | DRV | N(0,2) |
| `drv.dc_bus_voltage` | 直流母线电压 | V | 240–450 | 10 | DRV | N(0,0.5) |
| **`drv.efficiency`** | 电机系统效率 | ratio | 0.70–0.97 | 1 | DRV | 派生 |
| `drv.regen_power` | 能量回收功率 | kW | 0–70 | 10 | — | 派生 |
| `drv.bearing_vib_rms` | 轴承振动 RMS（早期故障） | mm/s | 0–20 | 1 | DRV | N(0,0.05) |

### 3.3 充电系统域 `chg.*` — 11 信号

| sensor_type | 物理含义 | 单位 | 合理范围 | Hz | 健康域 | 噪声 |
|---|---|---|---|---|---|---|
| `chg.state` | 充电状态 | enum | `idle\|ac\|dc\|complete\|fault` | evt | ELE | 规则 |
| `chg.mode` | 充电模式 | enum | `ac_slow\|dc_fast` | evt | — | 规则 |
| `chg.power` | 充电功率 | kW | 0–250 | 1 | ELE | N(0,0.4) |
| `chg.voltage` | 充电电压 | V | 0–1000 | 1 | ELE | N(0,0.5) |
| `chg.current` | 充电电流 | A | 0–600 | 1 | ELE | N(0,1.0) |
| **`chg.connector_temp`** | **充电枪/座温度**（起火风险核心） | ℃ | −30 – 120 | 1 | ELE | N(0,0.5) |
| `chg.cc_cv_phase` | 恒流/恒压阶段 | enum | `cc\|cv\|taper` | 1 | — | 规则 |
| `chg.session_energy` | 本次充入电量 | kWh | 0–120 | 1 | — | 派生 |
| `chg.session_duration` | 本次充电时长 | min | 0–900 | 1 | — | 派生 |
| `chg.target_soc` | 目标 SOC（用户设定） | % | 50–100 | evt | — | 用户 |
| **`chg.fast_ratio_30d`** | **近 30 天快充占比** → L1 `fast_ratio` | ratio | 0–1 | d | BAT | 派生 |

### 3.4 底盘与行驶域 `chs.*` — 22 信号

`meta.position` ∈ `FL`/`FR`/`RL`/`RR`。

| sensor_type | 物理含义 | 单位 | 合理范围 | Hz | 健康域 | 噪声 |
|---|---|---|---|---|---|---|
| **`chs.tire_press_[FL/FR/RL/RR]`** | **四轮胎压**（Model Y 冷态标定 2.90 bar） | bar | 1.20–3.50 | 0.2 | TIRE | N(0,0.01)+RW |
| `chs.tire_temp_[FL/FR/RL/RR]` | 四轮胎温 | ℃ | −30 – 90 | 0.2 | TIRE | N(0,0.5) |
| **`chs.brake_pad_[FL/FR/RL/RR]`** | **制动片剩余厚度**（新片 12mm） | mm | 0–12 | d | BRK | 单调递减 |
| `chs.brake_fluid_level` | 制动液液位 | % | 0–100 | 0.1 | BRK | 单调递减 |
| `chs.brake_disc_temp_front` | 前制动盘温度 | ℃ | −30 – 600 | 1 | BRK | N(0,3) |
| `chs.susp_travel_[FL/FR/RL/RR]` | 悬架位移（0=静平衡） | mm | −120 – 120 | 50 | BODY | 路面激励 |
| **`chs.speed`** | 车速 | km/h | 0–250 | 10 | — | N(0,0.3) |
| **`chs.accel_long`** | 纵向加速度（急加速/急刹判据） | m/s² | −10.0 – 6.0 | 50 | — | N(0,0.05) |
| `chs.accel_lat` | 横向加速度 | m/s² | −9.0 – 9.0 | 50 | — | N(0,0.05) |
| `chs.yaw_rate` | 横摆角速度 | °/s | −60 – 60 | 50 | — | N(0,0.2) |
| `chs.steering_angle` | 方向盘转角 | ° | −540 – 540 | 50 | — | N(0,0.3) |
| `chs.wheel_speed_[FL/FR/RL/RR]` | 四轮轮速（打滑判据） | rpm | 0–1800 | 50 | — | N(0,1) |
| `chs.abs_active` | ABS 介入 | bool | 0/1 | evt | BRK | 规则 |
| `chs.esc_active` | ESC 介入 | bool | 0/1 | evt | — | 规则 |

### 3.5 热管理域 `thm.*` — 9 信号

| sensor_type | 物理含义 | 单位 | 合理范围 | Hz | 健康域 | 噪声 |
|---|---|---|---|---|---|---|
| **`thm.coolant_temp_battery`** | **电池回路冷却液温度** | ℃ | −30 – 60 | 1 | THM | N(0,0.3) |
| `thm.coolant_temp_motor` | 电驱回路冷却液温度 | ℃ | −30 – 95 | 1 | THM | N(0,0.3) |
| `thm.coolant_flow` | 冷却液流量 | L/min | 0–40 | 1 | THM | N(0,0.2) |
| `thm.heat_pump_state` | 热泵状态 | enum | `off\|heating\|cooling\|defrost` | evt | THM | 规则 |
| `thm.compressor_speed` | 压缩机转速 | rpm | 0–8500 | 1 | THM | N(0,20) |
| `thm.cabin_temp` | 座舱实际温度 | ℃ | −20 – 60 | 0.2 | BODY | N(0,0.2) |
| `thm.cabin_set_temp` | 座舱设定温度 | ℃ | 16–30 | evt | — | 用户 |
| `thm.hvac_power` | 空调系统功耗 | kW | 0–7 | 1 | BODY | 派生 |
| `thm.radiator_fan_duty` | 散热风扇占空比 | % | 0–100 | 1 | THM | 规则 |

### 3.6 环境域 `env.*` — 8 信号

| sensor_type | 物理含义 | 单位 | 合理范围 | Hz | 健康域 | 噪声 |
|---|---|---|---|---|---|---|
| `env.gps_lat` 🔒 | 纬度 **（PII，见 §8）** | ° | −90 – 90 | 1 | — | N(0,3e-5) |
| `env.gps_lon` 🔒 | 经度 **（PII，见 §8）** | ° | −180 – 180 | 1 | — | N(0,3e-5) |
| `env.altitude` | 海拔（影响能耗/爬坡） | m | −150 – 5500 | 1 | — | N(0,1.5) |
| `env.gps_hdop` | 定位精度因子 | — | 0.5–20 | 1 | — | 规则 |
| **`env.ambient_temp`** | **环境温度** → L1 `ambient_temp` | ℃ | −40 – 55 | 0.1 | — | 季节+N(0,1) |
| `env.humidity` | 相对湿度 | % | 0–100 | 0.1 | — | N(0,3) |
| `env.road_type` | 路况 | enum | `urban\|highway\|mountain\|offroad` | evt | — | 马尔可夫 |
| `env.weather` | 天气 | enum | `clear\|rain\|snow\|fog` | evt | — | 马尔可夫 |

### 3.7 整车域 `veh.*` — 12 信号

| sensor_type | 物理含义 | 单位 | 合理范围 | Hz | 健康域 | 噪声 |
|---|---|---|---|---|---|---|
| **`veh.odometer`** | 累计里程 → L1 `mileage_km` | km | 0–500000 | d | — | 单调递增 |
| `veh.trip_distance` | 本次行程里程 | km | 0–1200 | 1 | — | 派生 |
| **`veh.energy_consumption`** | **百公里能耗** | kWh/100km | 8–35 | 1 | — | 派生 |
| `veh.range_estimate` | 剩余续航估计 | km | 0–700 | 1 | — | 派生 |
| `veh.gear` | 档位 | enum | `P\|R\|N\|D` | evt | — | 规则 |
| `veh.drive_mode` | 驾驶模式 | enum | `chill\|standard\|sport` | evt | — | 用户 |
| **`veh.aux_batt_voltage`** | **12V 低压蓄电池电压**（P0562 判据） | V | 9.0–15.0 | 0.1 | ELE | N(0,0.05) |
| `veh.door_state` | 车门状态位图（4门+后备箱+前舱） | bitmask | 0–63 | evt | BODY | 规则 |
| `veh.window_state` | 车窗开度位图 | bitmask | 0–15 | evt | BODY | 规则 |
| `veh.light_state` | 灯光状态位图（近/远/雾/转向/刹车） | bitmask | 0–31 | evt | BODY | 规则 |
| `veh.seatbelt_state` | 安全带位图 | bitmask | 0–31 | evt | — | 规则 |
| **`veh.hvil_status`** | **高压互锁回路**（0=断开，致命） | bool | 0/1 | 1 | ELE | 规则 |

### 3.8 CAN 总线与诊断域 `dtc.*` — 5 信号

| sensor_type | 物理含义 | 单位 | 合理范围 | Hz | 健康域 | 噪声 |
|---|---|---|---|---|---|---|
| **`dtc.active_codes`** | 当前激活 DTC 列表（JSON in `meta`） | list | 见下表 | evt | 各域 | 规则 |
| `dtc.pending_codes` | 待确认 DTC（未达确认次数） | list | 同上 | evt | — | 规则 |
| `dtc.can_bus_load` | CAN 总线负载率 | % | 0–100 | 1 | ELE | N(0,1.5) |
| `dtc.can_error_count` | CAN 错误帧计数 | int | 0–65535 | 1 | ELE | 泊松 |
| `dtc.ecu_heartbeat_miss` | ECU 心跳丢失计数 | int | 0–1000 | 1 | ELE | 泊松 |

#### DTC 码字典（严格复用 `simulator/constants.py::DTC_CODES` 的 7 码）

| DTC | 语义 | `fault_logs.system` | 默认 `fault_level` | 触发信号 |
|---|---|---|---|---|
| `P0AA6` | 动力电池绝缘故障 | `battery` | `critical` | `bat.insulation_resistance` |
| `P0CE0` | 驱动电机过温 ⚠️项目内约定 | `engine` | `high` | `drv.stator_temp_*` |
| `P1E00` | BMS 请求限功率 ⚠️OEM 自定义段 | `battery` | `medium` | `bat.max_*_power_allow` |
| `P0562` | 12V 系统电压过低 | `electronics` | `medium` | `veh.aux_batt_voltage` |
| `C0123` | 底盘/制动系统异常 | `brake` | `high` | `chs.brake_pad_*`, `chs.abs_active` |
| `U0100` | 与 ECM/PCM 通信丢失 | `electronics` | `high` | `dtc.ecu_heartbeat_miss` |
| `P0301` | 1 缸失火 ⚠️**内燃机码，BEV 语义错误** | `engine` | `medium` | 见 §9.2 缺陷 #1 |

> ⚠️ **诚实标注**：`P0CE0` 与 `P1E00` 的上述语义是**项目内约定**，非 SAE J2012 权威定义（P1xxx 本就是 OEM 自定义段）。`P0301` 是内燃机失火码，用在纯电车队上属于语义错误，建议替换 —— 详见 §9.2。**这三条在对外文档/用户可见文案中不应宣称为"标准 OBD 释义"。**

**信号总计：24 + 13 + 11 + 22 + 9 + 8 + 12 + 5 = 104**

---

## 4. 信号相关性规则（物理合理性的核心）

> **设计原则：先算物理，后加噪声。**
> 错误做法：对 104 个信号各自 `random.gauss()` —— 会产生"车速 0 但电机 8000rpm""SOC 掉 20% 但里程没动"这类一眼假的数据。
> 正确做法：先由 **7 条守恒/耦合方程**推出各信号的**确定性主值**，再只对**测量残差**加噪声（且残差之间用 Cholesky 保留相关性）。

### 4.1 七条主方程

#### C1 能量守恒：里程 ↔ 能耗 ↔ SOC ↔ 循环数

```
E_trip   = distance_km × consumption_kwh_100km / 100          # 本段耗电 kWh
ΔSOC     = −100 × E_trip / (capacity_kwh × SOH/100)           # SOC 下降
Δcycles  = E_throughput / capacity_kwh                        # 等效循环（充+放各算半循环）
odometer += distance_km
```

**这条是所有"联动感"的来源**：用户在前端把里程调大 → 自动带出 SOC 下降、循环数上升、SOH 加速衰减。反之亦然。

#### C2 能耗模型：温度 / 胎压 / 车速 / 驾驶风格 → 百公里能耗

```
consumption = base_kwh_100km
            × f_speed(v) × f_temp(T_amb) × f_tire(P) × f_hvac × f_style × f_road
```

| 因子 | 公式 | 说明 |
|---|---|---|
| `base` | Model Y ≈ **14.5** kWh/100km | 按车型标定 |
| `f_speed(v)` | `0.85 + 0.0035·(v−60) + 0.000055·(v−60)²` | U 型：60–80km/h 最省，高速风阻 ∝v² |
| `f_temp(T)` | `1 + 0.011·max(0, 18−T) + 0.006·max(0, T−30)` | **低温惩罚显著大于高温**（热泵制热耗能） |
| `f_tire(P)` | `1 + 0.09·max(0, (P_spec − P_avg)/P_spec)` | 胎压每低 10% ≈ 能耗 +0.9% |
| `f_hvac` | `1 + hvac_power/(v×base/100+ε)` | 低速时空调占比急剧升高（堵车工况） |
| `f_style` | gentle 0.92 / moderate 1.00 / aggressive 1.15 | 来自 `profile.driving_style` |
| `f_road` | urban 1.10 / highway 0.95 / mountain 1.25 | 来自 `env.road_type` |

> **冬季续航打折**这个用户最有体感的现象，就由 `f_temp` 产生：−10℃ 时 `f_temp ≈ 1.31`，续航掉 ~24%，符合真实 BEV 表现。

#### C3 电热耦合：电流 → 温升 → 内阻 → 电压（集总热模型）

```
dT_cell/dt = ( I²·R_int − h·A·(T_cell − T_coolant) ) / (m·Cp)
```

- 产热项 `I²·R_int`：大电流放电/快充 → 温升快
- 散热项 `h·A·ΔT`：热管理介入（`thm.coolant_temp_battery` 下降）→ 温升被抑制
- 典型参数：`m·Cp ≈ 180 kJ/K`（60kWh 包），`h·A ≈ 0.12 kW/K`（液冷开启时 0.45）

#### C4 内阻的双重依赖：温度 ↓ 则内阻 ↑；SOH ↓ 则内阻 ↑

```
R_int = R_25 × [ 1 + β·(25 − T_cell) ]        # 低温升阻，β ≈ 0.021 /℃ (T<25)
              × [ 1 + γ·(100 − SOH)/100 ]     # 老化升阻，γ ≈ 1.6
```

- 25℃、SOH=100 → `R_int = R_25 ≈ 75 mΩ`
- **−10℃、SOH=100 → ≈ 130 mΩ**（低温内阻几乎翻倍，这是冬季功率受限的物理原因）
- 25℃、SOH=80 → ≈ 99 mΩ

> ⚠️ 需求描述里写的"电芯温度↑ ↔ 内阻↓"**在常温区间成立但不能外推**：温度超过约 45℃ 后内阻不再下降，且触发热预警与限功率。模型用 `T<25` 分段，>25℃ 段取 `β≈0`，避免高温时算出荒谬的低内阻。

#### C5 端电压：OCV(SOC) 与欧姆压降

```
V_cell = OCV(SOC, chemistry) − I_cell × R_cell        # 放电 I>0 → 压降
V_pack = N_series × V_cell
```

- `OCV()` 用查表插值。**LFP 必须体现 20–90% SOC 的平坦平台**（≈3.28V，斜率 <0.15 mV/%），这是 LFP 车 SOC 跳变的物理来源。
- 单体离散：`V_min = V_avg − delta/2`，`V_max = V_avg + delta/2`

#### C6 单体一致性随老化发散

```
cell_volt_delta_mV = 8 + 1.9 × (100 − SOH) + 0.55 × cell_temp_delta + RW(σ=0.4)
```

- 新车 ≈ 8–15 mV；SOH 80% 时 ≈ 50 mV；SOH 72% 时 ≈ 65 mV+
- 与 `degradation.py::failure_probability(soh, cell_balance_dev)` 的 `fail_dev_weight=0.45` 直接咬合 —— **压差是故障概率的第二输入，不是装饰性字段**。

#### C7 胎压随温度漂移（理想气体 / Gay-Lussac）

```
P_abs_hot = P_abs_cold × (T_tire + 273.15) / (T_cold_ref + 273.15)
P_gauge   = P_abs − 1.013
```

- 冷态标定 2.90 bar @20℃ → **冬季 −10℃ 静置时表压掉到 ≈ 2.59 bar**，直接触发 TPMS 低压提示。
- 行驶后胎温升 15–25℃ → 表压回升 0.15–0.25 bar。
- 这条让"冬天早上胎压报警、开一段就消失"这个真实体验被复现出来。

### 4.2 SOH 退化 —— **复用既有引擎，禁止重写**

`carModel/simulator/degradation.py::step_soh()` 已实现且已用 NASA 曲线思路标定：

```
SOH(t+1) = SOH(t) − [ k_cycle·√Δcycles + k_temp·|T_cell−25| + k_fast·fast_ratio ]
                    × (1 + knee_alpha·(1 − SOH/100))          # 膝点加速
                    + k_maint·maintenance_event
```

**落地要求：模拟器直接 `from simulator.degradation import step_soh`，不得在 Guardian 侧另写一份衰减公式。** 否则 carModel 训练数据与 Guardian 展示数据的 SOH 轨迹会分叉，XGBoost 预测与页面显示对不上。

### 4.3 相关性矩阵（残差层，Cholesky 分解注入）

主值算完后，残差不能独立采样。至少保留以下相关：

| 信号对 | ρ | 物理原因 |
|---|---|---|
| `cell_temp_*` 8 路互相 | +0.85 | 同一包内热传导 |
| `tire_press_FL` ↔ `FR` | +0.75 | 同轴同批同工况 |
| `tire_press_前轴` ↔ `后轴` | +0.45 | 弱于同轴 |
| `stator_temp` ↔ `inverter_temp` | +0.70 | 共冷却回路 |
| `pack_current` ↔ `phase_current` | +0.95 | 同一功率流 |
| `ambient_temp` ↔ `cell_temp_avg` | +0.60 | 环境热耦合（有滞后） |
| `speed` ↔ `motor_rpm` | +0.99 | 固定速比刚性约束 |

> 实现：构造 7×7 相关阵 `Σ`，`L = cholesky(Σ)`，`residual = L @ standard_normal(7) * sigma_vec`。

### 4.4 刚性约束（生成后必须校验，违反即视为 bug）

| # | 约束 | 说明 |
|---|---|---|
| K1 | `motor_rpm = speed × gear_ratio × 1000/60/(2π·r_wheel)` ±2% | 速比刚性，Model Y ≈ 9.0 |
| K2 | `cell_volt_min ≤ cell_volt_avg ≤ cell_volt_max` | 序关系 |
| K3 | `cell_temp_min ≤ cell_temp_avg ≤ cell_temp_max` | 序关系 |
| K4 | `odometer` 单调不减 | 里程不可回退 |
| K5 | `brake_pad_*` 单调不增（除非发生更换事件） | 磨损不可逆 |
| K6 | `SOH` 单调不增（除非维护恢复 `k_maint`） | 衰减不可逆 |
| K7 | `chg.state='idle'` ⇒ `chg.power = 0` | 状态一致性 |
| K8 | `gear='P'` ⇒ `speed = 0` 且 `torque ≈ 0` | 状态一致性 |
| K9 | `pack_power = pack_voltage × pack_current / 1000` ±1% | 电功率恒等式 |
| K10 | 每车每天 `vehicle_state_history` 恰好 1 行 | **`t_index` 命脉，见 §1.2** |

---

## 5. 异常注入与故障判定规则表

### 5.1 判定规则总表

`级别` 对应 `vehicle_health_items.level`；`风险` 对应 `vehicle_fault_logs.fault_level`。
`扣分` 为该项在所属健康域内的扣减值（见 §6）。

| # | 触发条件 | 故障类型 | DTC | system | 级别 | 风险 | 扣分 |
|---|---|---|---|---|---|---|---|
| **电池域 BAT** |
| B1 | `cell_temp_max > 50℃` | 电池过温 | `P1E00` | battery | warning | high | 18 |
| B2 | `cell_temp_max > 58℃` **或** 3min 内温升 >5℃/min | **热失控预警** | `P1E00` | battery | critical | critical | 60 |
| B3 | `cell_temp_max < −20℃` 且请求放电 | 低温功率受限 | `P1E00` | battery | info | low | 5 |
| B4 | `insulation_resistance < 500 Ω/V × V_pack`（400V → 200kΩ） | 绝缘下降 | `P0AA6` | battery | warning | high | 25 |
| B5 | `insulation_resistance < 100 Ω/V × V_pack` | **绝缘失效/漏电** | `P0AA6` | battery | critical | critical | 70 |
| B6 | `cell_volt_delta > 80 mV` | 单体一致性差 | `P1E00` | battery | warning | medium | 15 |
| B7 | `cell_volt_delta > 150 mV` | 单体严重失衡 | `P1E00` | battery | critical | high | 35 |
| B8 | `R_int > R_baseline × 1.35`（同温归一后） | 内阻突增/老化 | `P1E00` | battery | warning | medium | 14 |
| B9 | `SOH < 80%` | 电池容量衰减 | — | battery | warning | medium | 12 |
| B10 | `SOH < 70%`（`eol_soh`） | 电池达寿命终止 | — | battery | critical | high | 40 |
| B11 | `cell_volt_min < 化学体系下限` | 单体过放 | `P0AA6` | battery | critical | critical | 50 |
| **驱动域 DRV** |
| M1 | `stator_temp > 150℃` | 电机过温降功率 | `P0CE0` | engine | warning | medium | 20 |
| M2 | `stator_temp > 175℃` | 电机严重过温 | `P0CE0` | engine | critical | critical | 55 |
| M3 | `inverter_temp > 110℃` | 控制器过温 | `P0CE0` | engine | warning | medium | 18 |
| M4 | `efficiency < 0.80` 且 `rpm∈[2000,8000]` | 电机效率异常 | `P0CE0` | engine | warning | medium | 15 |
| M5 | `bearing_vib_rms > 7 mm/s` | 轴承磨损 | `P0301`⚠️ | engine | warning | medium | 16 |
| M6 | 前后轴 `torque` 偏差 >30% 且非主动扭矩分配 | 驱动扭矩不均 | `P0301`⚠️ | engine | warning | medium | 12 |
| **充电/电气域 ELE** |
| E1 | `connector_temp > 85℃` | 充电枪过温 | `P1E00` | electronics | warning | high | 22 |
| E2 | `connector_temp > 100℃` | **充电接口热失效** | `P1E00` | electronics | critical | critical | 60 |
| E3 | `chg.state='fault'` 连续 ≥2 次会话 | 充电系统故障 | `P1E00` | electronics | warning | medium | 20 |
| E4 | `aux_batt_voltage < 11.6V`（静置） | 12V 电压低 | `P0562` | electronics | warning | medium | 18 |
| E5 | `aux_batt_voltage < 10.8V` | **12V 亏电，有抛锚风险** | `P0562` | electronics | critical | high | 45 |
| E6 | `hvil_status = 0` | **高压互锁断开** | `P0AA6` | electronics | critical | critical | 80 |
| E7 | `ecu_heartbeat_miss > 10/min` | CAN 通信丢失 | `U0100` | electronics | warning | high | 25 |
| E8 | `can_bus_load > 85%` | 总线负载过高 | `U0100` | electronics | info | low | 6 |
| **轮胎域 TIRE** |
| T1 | 任一 `tire_press < 2.20 bar`（温补后） | 胎压偏低 | — | tire | warning | medium | 15 |
| T2 | 任一 `tire_press < 2.00 bar` | **胎压过低，爆胎风险** | `C0123` | tire | critical | high | 40 |
| T3 | 任一 `tire_press > 3.30 bar` | 胎压过高 | — | tire | warning | medium | 12 |
| T4 | 同轴左右压差 > 0.30 bar | 左右胎压不均 | — | tire | warning | medium | 10 |
| T5 | 单胎 30min 内压降 > 0.35 bar | **疑似慢漏气/扎胎** | `C0123` | tire | critical | high | 35 |
| T6 | `tire_temp > 80℃` | 轮胎过热 | — | tire | warning | medium | 14 |
| **制动域 BRK** |
| R1 | 任一 `brake_pad < 4.0 mm` | 制动片偏薄 | — | brake | warning | medium | 20 |
| R2 | 任一 `brake_pad < 2.5 mm` | **制动片需立即更换** | `C0123` | brake | critical | high | 50 |
| R3 | `brake_fluid_level < 30%` | 制动液不足 | `C0123` | brake | warning | high | 25 |
| R4 | `brake_disc_temp > 450℃` | 制动盘过热/热衰退 | — | brake | warning | medium | 15 |
| **热管理域 THM** |
| H1 | `coolant_temp_battery > 45℃` | 电池冷却不足 | — | — | warning | medium | 18 |
| H2 | `cell_temp_delta > 8℃` | 热管理不均匀 | — | — | warning | medium | 15 |
| H3 | `heat_pump_state='off'` 但 `cell_temp_max>45℃` | **热泵失效** | `P1E00` | body | critical | high | 40 |
| H4 | `coolant_flow < 3 L/min` 且压缩机运行 | 冷却液循环异常 | `P1E00` | body | warning | high | 25 |
| **车身域 BODY** |
| Y1 | `speed > 5` 且 `door_state != 0` | 行驶中车门未关 | — | body | critical | high | 30 |
| Y2 | 同轴 `susp_travel` 静态偏差 > 25mm | 悬架/弹簧异常 | — | body | warning | medium | 15 |

### 5.2 组合规则（单信号不报，组合才报）

真实车厂的诊断策略很少是单阈值，以下组合能显著提升"像真的"：

| # | 组合条件 | 结论 | 风险 |
|---|---|---|---|
| X1 | `B8`(内阻突增) **且** `B6`(压差大) **且** `SOH<85` | **电池组加速老化**，建议 4S 店检测 | high |
| X2 | `T1`(胎压低) **且** `energy_consumption` 环比 +8% | 胎压导致能耗上升（可自愈项） | low |
| X3 | `B1`(电芯过温) **且** `H1`(冷却液温高) **且** `chg.mode='dc_fast'` | 快充热管理能力不足 | medium |
| X4 | `M1`(电机过温) **且** `road_type='mountain'` **且** 持续 >20min | 长坡连续爬升过热（工况性，非故障） | low |
| X5 | `E4`(12V低) **且** 静置 >48h **且** 环境温度 <0℃ | 低温亏电，**大概率无法启动** | high |

> X4 展示了一个重要点：**同样的过温，工况不同结论不同**。只按阈值报警会让用户觉得"这车老是瞎报"，加了工况上下文才像真的。

### 5.3 异常注入策略（给模拟器用）

三种注入模式，供前端 what-if 与演示场景调用：

| 模式 | 用途 | 实现 |
|---|---|---|
| `natural` | 常态 | 由 `degradation.failure_probability(soh, cell_balance_dev)` 按日抽样，自然涌现故障 |
| `scenario` | 演示/测试固定剧本 | 指定 `fault_id`（如 `T2`），反解出满足条件的信号值并覆盖 |
| `stress` | 参数扫描/压测 | 沿某维度线性推进（如胎压 2.9→1.8 bar），观察健康分曲线与告警触发点 |

**反解示例**（`scenario` 模式注入 T2 胎压过低）：
```
target: chs.tire_press_FL = 1.92 bar
→ 连带修正（保持物理一致）:
   tire_temp_FL   += 6.5℃          # 低压 → 变形生热
   energy_consumption × 1.021      # C2 的 f_tire 因子
   → SOC 下降加快（C1）
   → 触发 T2 + 可能触发 X2
```
**注入必须走连带修正，否则会出现"胎压 1.9 但能耗完全没变"的穿帮。**

---

## 6. 健康分加权聚合公式

### 6.1 两级模型：8 物理域 → Guardian 6 列

Guardian 的 `vehicle_health_snapshots` 只有 6 个子分列（`engine/brake/tire/battery/body/electronics`），而物理上有 8 个域。**不做数据库迁移**，用投影矩阵解决：

| 物理域 | 代号 | 权重 | → 投影到 DB 列 |
|---|---|---|---|
| 动力电池 | BAT | **40%** | `battery_score` |
| 驱动电机 | DRV | **15%** | `engine_score` |
| 轮胎 | TIRE | **10%** | `tire_score` |
| 制动 | BRK | **10%** | `brake_score` |
| 热管理 | THM | **10%** | 拆分：电池热→`battery_score` / 电驱热→`engine_score` / 座舱热→`body_score` |
| 充电系统 | CHG | **7%** | `electronics_score` |
| 电气与 CAN | ELE | **5%** | `electronics_score` |
| 车身 | BODY | **3%** | `body_score` |
| | | **100%** | |

> **设计说明**：纯电车没有"engine"，但该列已被前端仪表盘、Agent 工具 `get_health_score` 引用。复用 `engine_score` 承载"驱动系统"语义，比加列迁移的改动面小一个数量级。**需在 API 文档与前端文案层做一次别名映射：`engine_score → "驱动系统"`。**

THM 的 10% 按 `6:3:1` 拆给电池热 / 电驱热 / 座舱热，故最终：

```
battery_score      ← BAT(40) + THM_bat(6)   = 46%
engine_score       ← DRV(15) + THM_mot(3)   = 18%
tire_score         ← TIRE(10)               = 10%
brake_score        ← BRK(10)                = 10%
electronics_score  ← CHG(7) + ELE(5)        = 12%
body_score         ← BODY(3) + THM_cab(1)   =  4%
                                    合计     = 100%
```

### 6.2 域内扣分制

```
domain_score = clamp(100 − Σ deduction_i × severity_factor_i , 0, 100)
```

- `deduction_i` = §5.1 表中该规则的"扣分"
- `severity_factor` = 越界程度的连续化（避免阈值处分数跳变）：

```
severity_factor = clamp( (x − x_warn) / (x_crit − x_warn), 0, 1.5 )
```

即：刚触及 warning 线时扣分接近 0，到 critical 线扣满分，超出后最多扣 1.5 倍。**这让用户拖动参数时看到的是平滑变化的分数，而不是突然从 84 跳到 61。**

### 6.3 总分

```
health_score = round( Σ_d ( w_d × domain_score_d ) )       # w_d 见 6.1
```

再叠加两项全局修正：

```
health_score −= 3 × count(active DTC, level=critical)
health_score −= 1 × count(active DTC, level=high)
health_score  = clamp(health_score, 0, 100)
```

**校验 demo 车**：小白（SOH≈96、里程 12800、无 critical 故障、5 条历史故障已 resolved）按此公式应落在 **88–93**，而非当前 seed 硬编码的 84。若要保留 84，需要有 1 条 active 的 medium 故障支撑（见 §9.2 缺陷 #2）。

### 6.4 风险等级判定（阈值 + 趋势）

只看当前值会漏掉"还没越界但掉得很快"的车。引入趋势项：

```
trend_d = EWMA_slope(domain_score_d, window=30d, alpha=0.15)   # 分/天，负值=恶化
days_to_warn = (domain_score_d − 60) / max(−trend_d, ε)        # 预计多少天跌破 60
```

| 风险等级 | 判定条件（取最严者） |
|---|---|
| `critical` | 存在 critical 级项 **或** `domain_score < 50` |
| `high` | 存在 high 级项 **或** `domain_score < 65` **或** `days_to_warn < 30` |
| `medium` | 存在 warning 级项 **或** `domain_score < 80` **或** `days_to_warn < 90` |
| `low` | 其余 |

> `days_to_warn` 是**给用户最有价值的一个数**："按当前衰减速度，你的电池还有 ~180 天跌到需要关注的水平"，比单纯一个 84 分有用得多。建议前端露出。

---

## 7. Seed 数据生成策略与关键函数签名

### 7.1 生成管线

```
VehicleProfile (静态画像)
      │
      ├─► ①  build_usage_calendar(profile, start, days)     # 每日行驶/充电计划
      │        马尔可夫链: 工作日通勤 / 周末出游 / 长途 / 静置
      │
      ├─► ②  for each day: simulate_day(...)                # 逐日推进
      │        ├─ propagate_physics()   C1–C7 主方程
      │        ├─ step_soh()            ← 复用 simulator/degradation.py
      │        └─ inject_noise()        Cholesky 相关残差
      │
      ├─► ③  to_state_row(day_state)  ──► vehicle_state_history (L1, 9列)
      │
      ├─► ④  to_sensor_snapshot(state) ──► vehicle_sensor_data (L0, 104信号)
      │
      └─► ⑤  score_health(state)       ──► health_snapshots + items + fault_logs (L2)
```

### 7.2 关键函数签名

```python
# ============ 数据结构 ============

@dataclass(frozen=True)
class VehicleProfile:
    """静态画像。前 6 个字段必须与 features.py::_STATIC 完全一致。"""
    vehicle_id: str
    capacity_kwh: float
    chemistry: Literal["LFP", "NMC", "NCA", "LMFP"]
    climate: Literal["cold", "temperate", "hot"]
    driving_style: Literal["gentle", "moderate", "aggressive"]
    charge_style: Literal["slow", "fast_mix"]
    dod: Literal["shallow", "deep"]
    # ---- 以下为模拟器扩展，不进 XGBoost ----
    n_series: int = 106            # 串联单体数
    base_consumption: float = 14.5 # kWh/100km
    gear_ratio: float = 9.0
    wheel_radius_m: float = 0.3565
    tire_press_spec_bar: float = 2.90
    brake_pad_new_mm: float = 12.0


@dataclass
class DayState:
    """单日推进后的完整车辆状态（L0 全量 + L1 投影所需）。"""
    date: date
    signals: dict[str, float | str | bool]   # 104 个 sensor_type -> value
    faults: list[FaultEvent]
    # L1 九列在 signals 里，由 to_state_row() 抽取


# ============ ① 使用日历 ============

def build_usage_calendar(
    profile: VehicleProfile,
    start: date,
    days: int,
    rng: np.random.Generator,
) -> list[DayPlan]:
    """生成每日使用计划：里程、行程数、快充次数、静置时长、路况分布。

    马尔可夫状态: commute(0.62) / weekend_trip(0.16) / long_haul(0.05) / idle(0.17)
    转移矩阵按 profile.driving_style 调整；周末/节假日提高 weekend_trip 概率。
    输出的 distance_km 服从对数正态，避免出现"每天恰好 42km"的机器味。
    """


# ============ ② 逐日物理推进 ============

def simulate_day(
    profile: VehicleProfile,
    prev: DayState | None,
    plan: DayPlan,
    weather: WeatherSample,
    rng: np.random.Generator,
) -> DayState:
    """单日状态转移。纯函数：(prev, plan, weather, rng) 唯一决定 next。

    顺序严格如下（依赖关系不可换）:
      1. ambient_temp/humidity  ← weather
      2. consumption            ← C2 (依赖 ambient, tire_press(prev), speed, style)
      3. E_trip / ΔSOC / Δcycles/ odometer ← C1
      4. R_int                  ← C4 (依赖 cell_temp, soh(prev))
      5. cell_temp              ← C3 集总热模型 (依赖 I, R_int, coolant)
      6. V_cell / V_pack        ← C5 (依赖 SOC, I, R_int)
      7. cell_volt_delta        ← C6 (依赖 soh)
      8. soh                    ← degradation.step_soh()   【复用，勿重写】
      9. tire_press             ← C7 (依赖 ambient, tire_temp) + 慢漏项
     10. brake_pad              ← 磨损累积 (依赖 hard_brake, distance)
     11. 其余从动信号            ← 派生
     12. inject_correlated_noise()
     13. assert_invariants()    ← K1–K10 校验
    """


def propagate_thermal(
    cell_temp_prev: float, current_a: float, r_int_ohm: float,
    coolant_temp: float, dt_s: float, m_cp_kj_k: float = 180.0,
    ha_kw_k: float = 0.12,
) -> float:
    """C3 集总热模型一步积分。液冷开启时 ha_kw_k 取 0.45。"""


def ocv_lookup(soc_pct: float, chemistry: str) -> float:
    """C5 开路电压查表插值。LFP 必须体现 20–90% 平坦平台。"""


# ============ ③ L1 投影（喂 XGBoost）============

def to_state_row(day: DayState) -> StateRow:
    """104 信号 → vehicle_state_history 的 9 列。

    严格映射（列名不可改，见 §1.1）:
        soh          = bat.soh
        soc          = bat.soc            (当日结束时刻)
        temp         = bat.cell_temp_avg  (当日行驶时段均值，非全天均值)
        ambient_temp = env.ambient_temp   (当日均值)
        mileage_km   = veh.odometer       (累计值，非当日增量)
        cycles       = bat.charge_cycles  (累计值)
        fast_ratio   = chg.fast_ratio_30d
        hard_accel   = count(accel_long > +3.0 m/s²)
        hard_brake   = count(accel_long < −3.5 m/s²)
        failure      = 1 if any(fault.level == 'critical') else 0

    ⚠️ mileage_km/cycles 是累计量，temp/ambient 是均值 —— 训练侧
       extract_features 对二者的用法不同(delta vs mean)，写反会静默降低模型精度。
    """


# ============ ④ L0 快照 ============

def to_sensor_rows(day: DayState, vehicle_id: int) -> list[VehicleSensorData]:
    """104 信号 → EAV 行。多点信号用 meta 区分:
        tire_press  -> meta={"position": "FL"}
        cell_temp   -> meta={"channel": 3}
        stator_temp -> meta={"axle": "front"}
       非标量信号(dtc.active_codes)存 meta，sensor_value 存 len()。
    """


# ============ ⑤ L2 健康分 ============

def score_health(day: DayState, history: list[DayState]) -> HealthResult:
    """§5 规则表 + §6 加权公式 → 6 个子分 + 总分 + items + faults。
       history 仅用于趋势项 (EWMA slope, days_to_warn)，长度 30 天足够。
    """


# ============ 顶层入口 ============

def generate_history(
    profile: VehicleProfile, start: date, days: int, seed: int,
) -> list[DayState]:
    """回填历史。⚠️ 保证每天恰好 1 行 —— t_index 命脉 (§1.2)。"""


def simulate_snapshot(
    profile: VehicleProfile,
    overrides: dict[str, float] | None = None,
    seed: int | None = None,
) -> tuple[DayState, HealthResult]:
    """【what-if 入口】纯函数，不落库。

    overrides 例: {"chs.tire_press_FL": 1.9, "bat.soh": 82.0}
    流程: 取当前快照 → 应用 overrides → 连带修正(§5.3) → 重算 L1/L2 → 返回
    前端拖参数走这个，只读不写。
    """
```

### 7.3 可复现性

```python
seed = int(hashlib.sha256(f"{vehicle_id}|{date}|{salt_version}".encode()).hexdigest()[:16], 16)
rng  = np.random.default_rng(seed)
```

- **每日独立派生 seed**，而非全局单 RNG。好处：重放第 500 天不必重跑前 499 天；并行生成车队结果一致。
- `salt_version` 复用 `vehicle_registry.salt_version`，改版本即可整体换一批数据而不撞历史。
- 验收：同 `(vehicle_id, date, salt_version)` 两次生成，104 信号逐字段 `==`。

### 7.4 what-if 的三条硬规则

1. **只读**：`simulate_snapshot()` 全程不碰 DB，前端拖动 100 次不产生 100 行垃圾数据。
2. **连带修正**：override 一个信号必须按 §4 主方程更新下游（改胎压→改能耗→改 SOC）。只改单点是穿帮的主要来源。
3. **标注来源**：返回体带 `provenance: {"bat.soh": "user_override", "bat.soc": "derived"}`，复用 `vehicle_state_v2.py` 已有的 provenance 机制，前端可把用户改过的值高亮，避免用户误以为是真实读数。

### 7.5 性能预算

| 操作 | 规模 | 预估耗时 | 说明 |
|---|---|---|---|
| `simulate_day()` | 1 车 1 天 | ~0.4 ms | 纯 numpy 标量运算 |
| `generate_history()` | 1 车 3 年 | ~1.3 s | 1095 天 |
| 车队回填 | 100 车 3 年 | ~2.5 min | 建议 `multiprocessing`，各车独立可并行 |
| `simulate_snapshot()` | 1 次 what-if | **~2 ms** | 满足前端实时拖动 (<16ms/帧) |
| L0 落库 | 104 行/车 upsert | ~8 ms | 只存当前快照，不存时序 |

> 车队回填走**分块提交**（每 500 天一次 `commit`），避免单事务过大撑爆 WAL。

---

## 8. 隐私与脱敏（PII 处理）

模拟数据虽为合成，但 schema 会**原样承接真实车辆接入**，脱敏规则必须在建模期就定下来，否则真车接入时来不及改。

| 字段 | PII 等级 | 风险 | 脱敏方案 |
|---|---|---|---|
| `env.gps_lat` / `env.gps_lon` | **高** | 可反推家庭住址、工作单位、日常轨迹 | 展示层 **geohash 截断到 5 位**（±2.4km）；原始精度仅在 `consent.scope` 含 `location` 时保留；轨迹存储做**首尾各裁剪 500m** |
| `vehicles.vin` | **高** | 全球唯一，可关联车主实名、维修记录 | 展示层掩码 `LSJW32E78***00017`（保留前 8 位 WMI+VDS 与后 5 位）；日志与 embedding **一律用 `vehicle_id` 代号** |
| `vehicles.plate_number` | **高** | 直接关联车主 | 展示层 `沪A·D****`；导出数据集**整列剔除** |
| `users.phone` / `email` | **高** | 直接 PII | HMAC-SHA256 + per-tenant salt，不可逆；仅存哈希用于去重 |
| `insurance_policy_no` | 中 | 可关联保单与身份 | 掩码保留后 4 位 |
| `env.altitude` + 时间序列 | 中 | 与 GPS 组合可提升定位精度 | 与 GPS 同级管控 |
| `veh.odometer` | 低 | 单独无害 | 明文 |

**落地要求：**
- 脱敏在 **API 序列化层**统一做（`schemas/` 的 response model），不在业务层各写一遍 —— 否则必然有遗漏路径泄漏原值。
- 数据集导出走独立的 `export_dataset()`，默认 **deny-list 全部高危字段**，需要原值必须显式传 `include_pii=True` 并记审计日志（`audit_store.db` 已存在，可直接用）。
- 合成数据的 GPS 轨迹**不要用真实住宅坐标**做种子。建议锚定城市级公开 POI（如"上海人民广场"）加随机偏移，避免"看起来像某个真实地址"的尴尬。
- `consent` 机制已在 `schema/vehicle_state_v2.py::Consent(granted/scope/data_residency)` 定义，**直接复用，不要另起炉灶**。

---

## 9. 落地清单与风险

### 9.1 建议实施顺序

| 阶段 | 内容 | 依赖 | 产出 |
|---|---|---|---|
| P0 | 落 `VehicleProfile` + `simulate_day()` C1/C2/C5 三条主方程 | — | 单车能跑出合理 SOC/里程/能耗曲线 |
| P1 | 接 `degradation.step_soh()`，补 C3/C4/C6，回填 3 年历史 | P0 | `vehicle_state_history` 可喂 XGBoost |
| P2 | `score_health()` + §5 规则表 → 6 子分 | P1 | 健康分不再是硬编码 84 |
| P3 | `to_sensor_rows()` 落 L0 快照 | P1 | 前端 104 信号仪表盘 |
| P4 | `simulate_snapshot()` what-if 接口 | P2 | 用户拖参数实时看引擎反馈 |
| P5 | 脱敏层 + 数据集导出 | P3 | 合规交付 |

### 9.2 ⚠️ 发现的既有数据质量问题（建议本次一并修）

**缺陷 #1：`P0301` 用于纯电车队属语义错误**
`simulator/constants.py::DTC_CODES` 含 `P0301`（Cylinder 1 Misfire，内燃机 1 缸失火）。当前车队 `fuel_type` 全为 `electric`，纯电车不存在气缸，一旦这个码出现在用户可见的故障列表里，**懂车的用户会立刻判定数据是编的**。
- 建议：把 `P0301` 替换为 `P0A3F`（Drive Motor "A" Position Sensor Circuit，SAE 标准 EV 码）或 `P0C76`。
- 影响面：`constants.py` 一处常量 + 已生成的历史 fault_logs 需一次性 UPDATE 迁移。
- ⚠️ 该码在 `fleet.py` 与 `life_simulator.py` 都会读，改常量即可全局生效（口径已于早前统一到 `constants.py`）。

**缺陷 #2：demo 车里程/健康分与需求描述不一致**
- `seed_data.py` 硬编码 `mileage=12800`，团队需求描述为 `12,692km`。
- 健康分 84 是**硬编码常量**，不由任何信号推导；按 §6.3 公式该车应为 88–93。
- 建议：P2 阶段把 84 改为 `score_health()` 计算值；若产品希望保留"有点小毛病"的观感，应显式 seed 一条 active 的 medium 故障（如 `T1` 胎压偏低）来支撑分数，而不是硬编码一个数字。
- **未核实项**：需求里的"5 次故障"我在 `seed_data.py` 未逐条核对，请后端确认 `vehicle_fault_logs` 实际 seed 条数与 `repair_status` 分布。

**缺陷 #3（提示，非阻塞）**：`vehicle_sensor_data` 是 EAV 且 `sensor_value` 为单一 `Float`，枚举型信号（`chg.state`、`veh.gear`、`env.weather`）无法直接存。
- 建议：枚举存 `meta={"enum": "dc_fast"}`，`sensor_value` 存序号；或在 `sensor_type` 命名上区分。**需要后端确认一个统一约定**，否则各处写法不一。

### 9.3 遗留风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| L0 全量时序若真要落库 | SQLite 撑不住（~9000 万点/车/天） | 当前设计只落快照；如需时序，迁 TimescaleDB（`sensor_data.py` 注释已预留） |
| §4 物理系数未经真实车辆标定 | 数值"物理合理"但非"特斯拉真实值" | **标注为待标定**；有真实数据后按 `nasa_calibrate.py` 同样的思路回归 |
| 104 信号一次性铺开 | 前端与后端工作量大 | 按 §9.1 分阶段，P0–P2 只需 ~20 个信号即可跑通闭环 |
| `engine_score` 承载"驱动系统" | 语义别扭，新人易误解 | API/前端做别名映射，并在 `health_snapshot.py` 补注释 |

### 9.4 待人工复核项（我无法自证的部分）

1. §4 全部物理系数（`β=0.021`、`γ=1.6`、`m·Cp=180kJ/K`、`base=14.5kWh/100km` 等）为**物理合理的工程初值**，非实测标定值。不应对外宣称为"特斯拉实测参数"。
2. §5 各阈值（50℃/58℃/2.20bar/4.0mm 等）参考通用行业经验与 GB 要求量级，**未逐条核对 Model Y 具体标定手册**。
3. `P0CE0`/`P1E00` 的语义为项目内约定（见 §3.8 标注）。
4. Demo 车「小白」实际 seed 的故障条数与分布未逐条核对（见缺陷 #2）。

---

## 附录 A：L1 九列投影速查

| L1 列 | 来源信号 | 聚合方式 | 易错点 |
|---|---|---|---|
| `soh` | `bat.soh` | 当日末值 | 单调不增 |
| `soc` | `bat.soc` | 当日末值 | 非均值 |
| `temp` | `bat.cell_temp_avg` | **行驶时段**均值 | 用全天均值会被静置稀释 |
| `ambient_temp` | `env.ambient_temp` | 当日均值 | — |
| `mileage_km` | `veh.odometer` | **累计值** | 不是当日增量 |
| `cycles` | `bat.charge_cycles` | **累计值** | 不是当日增量 |
| `fast_ratio` | `chg.fast_ratio_30d` | 30 日滚动 | NaN 时训练侧回填 0.3 |
| `hard_accel` | `chs.accel_long` | `count(>+3.0)` | 当日计数 |
| `hard_brake` | `chs.accel_long` | `count(<−3.5)` | 当日计数 |
| `failure` | faults | `any(critical)` | 0/1 |

## 附录 B：健康域 ↔ DB 列速查

| 物理域 | 权重 | DB 列 | 主要信号 |
|---|---|---|---|
| BAT | 40% | `battery_score` | soh, cell_volt_delta, internal_resistance, insulation_resistance, cell_temp_max |
| DRV | 15% | `engine_score` | stator_temp, inverter_temp, efficiency, bearing_vib |
| TIRE | 10% | `tire_score` | tire_press ×4, tire_temp ×4 |
| BRK | 10% | `brake_score` | brake_pad ×4, brake_fluid_level, disc_temp |
| THM | 10% | 拆 6:3:1 → battery/engine/body | coolant_temp_*, cell_temp_delta, heat_pump_state |
| CHG | 7% | `electronics_score` | connector_temp, chg.state |
| ELE | 5% | `electronics_score` | aux_batt_voltage, hvil_status, can_error_count |
| BODY | 3% | `body_score` | door_state, susp_travel, cabin_temp |

---

*文档结束 · 有疑问找 dataengineer（数匠）*

