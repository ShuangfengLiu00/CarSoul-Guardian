/**
 * Dashboard 演示兜底数据
 *
 * 当后端不可用或无车辆数据时，使用这组数据渲染丰富的可视化图表，
 * 保证平板/触摸大屏演示场景下 Dashboard 始终有内容。
 * 数据风格与 StoryMode 的电池热失控守护剧情一致。
 */
import type {
  Vehicle,
  VehicleArchive,
  HealthSnapshot,
  DrivingBehavior,
  Alert,
  MaintenanceRecord,
  MaintenanceSchedule,
  LifecycleEvent,
  OwnershipRecord,
  DigitalTwin,
} from "./types";

const now = Date.now();
const day = 86400000;

export const DEMO_VEHICLE: Vehicle = {
  id: 1001,
  brand: "Tesla",
  model: "Model Y",
  year: 2023,
  vin: "5YJYGDEE1MF100001",
  plate_number: "京A·DC2025",
  color: "午夜银",
  nickname: "小银",
  fuel_type: "electric",
  mileage: 38420,
  status: "active",
  purchase_date: "2023-06-15",
  purchase_price: 298000,
  insurance_company: "中国人保",
  insurance_expiry: "2026-08-15",
  registration_date: "2023-06-20",
  inspection_expiry: "2027-06-20",
  battery_capacity: 75,
  created_at: "2023-06-15T08:00:00Z",
  updated_at: new Date(now).toISOString(),
};

// 近 12 次健康快照（呈现下降后回升的守护曲线）
export const DEMO_HEALTH_HISTORY: HealthSnapshot[] = Array.from({ length: 12 }).map((_, i) => {
  const t = new Date(now - (11 - i) * 2 * 3600 * 1000).toISOString();
  // 92 -> 88 -> 81 -> 73 -> 65(谷) -> 70 -> 78 -> 84 -> 88
  const curve = [92, 90, 88, 81, 73, 65, 70, 78, 84, 88, 89, 90];
  const score = curve[i];
  return {
    id: 1000 + i,
    vehicle_id: 1001,
    health_score: score,
    mileage: 38420 - (11 - i) * 60,
    engine_score: 90,
    brake_score: score + 2,
    tire_score: score - 3,
    battery_score: i >= 3 && i <= 5 ? score - 20 : score, // 电池在异常期明显低
    body_score: 95,
    electronics_score: 88,
    summary:
      i === 5
        ? "电池温度异常上升，冷却效率下降，触发主动守护"
        : i >= 6
          ? "主动守护后温度回落，健康指数回升"
          : "各项系统运转正常",
    source: "digital_twin",
    snapshot_time: t,
    items: [],
  };
});

export const DEMO_LATEST_HEALTH: HealthSnapshot = DEMO_HEALTH_HISTORY[DEMO_HEALTH_HISTORY.length - 1];

// 近 14 天驾驶行为
export const DEMO_DRIVING_BEHAVIORS: DrivingBehavior[] = Array.from({ length: 14 }).map((_, i) => {
  const d = new Date(now - (13 - i) * day).toISOString().slice(0, 10);
  return {
    id: 2000 + i,
    vehicle_id: 1001,
    record_date: d,
    trip_count: 2 + Math.round(Math.random() * 3),
    total_distance: 28 + Math.round(Math.random() * 45),
    total_duration: 2400 + Math.round(Math.random() * 1800),
    avg_speed: 38 + Math.round(Math.random() * 12),
    max_speed: 88 + Math.round(Math.random() * 18),
    safety_score: 78 + Math.round(Math.random() * 16),
    eco_score: 82 + Math.round(Math.random() * 12),
    harsh_acceleration_count: Math.round(Math.random() * 3),
    harsh_braking_count: Math.round(Math.random() * 2),
    sharp_turn_count: Math.round(Math.random() * 2),
    overspeed_count: Math.round(Math.random() * 1),
    idle_duration: 300 + Math.round(Math.random() * 600),
    fuel_consumption: undefined,
    energy_efficiency: 14.2 + Math.random() * 2,
    created_at: new Date(now - (13 - i) * day).toISOString(),
  };
});

export const DEMO_ALERTS: Alert[] = [
  {
    id: 3001,
    vehicle_id: 1001,
    alert_type: "battery_thermal",
    level: "critical",
    category: "电池系统",
    title: "电池温度异常 · 热失控风险",
    detail:
      "电池组温度已达 43.2℃，超过安全阈值 40℃，冷却效率降至 62%。CarSoul Agent 已在风险演变为故障前主动识别，并启动守护闭环。",
    recommendation: "已远程启动电池主动冷却，并将推送通知车主。建议近期前往服务中心检测。",
    status: "active",
    triggered_at: new Date(now - 18 * 60 * 1000).toISOString(),
  },
  {
    id: 3002,
    vehicle_id: 1001,
    alert_type: "tire_pressure",
    level: "warning",
    category: "轮胎系统",
    title: "左前轮胎压偏低",
    detail: "左前轮胎压 2.1 bar，低于推荐值 2.3 bar。",
    recommendation: "建议尽快补充胎压。",
    status: "active",
    triggered_at: new Date(now - 2 * 3600 * 1000).toISOString(),
  },
  {
    id: 3003,
    vehicle_id: 1001,
    alert_type: "maintenance",
    level: "warning",
    category: "保养",
    title: "下次保养即将到期",
    detail: "距下次保养还有 320 km。",
    status: "active",
    triggered_at: new Date(now - 6 * 3600 * 1000).toISOString(),
  },
  {
    id: 3004,
    vehicle_id: 1001,
    alert_type: "driving",
    level: "info",
    category: "驾驶行为",
    title: "本周急刹车次数下降",
    detail: "本周急刹车 3 次，较上周下降 40%。",
    status: "resolved",
    triggered_at: new Date(now - 2 * day).toISOString(),
    resolved_at: new Date(now - day).toISOString(),
  },
];

export const DEMO_MAINTENANCE_RECORDS: MaintenanceRecord[] = [
  {
    id: 4001,
    vehicle_id: 1001,
    maintenance_type: "routine",
    category: "常规",
    title: "5000km 常规保养",
    maintenance_date: "2024-12-10",
    mileage: 32000,
    cost: 680,
    service_provider: "Tesla 服务中心",
    created_at: "2024-12-10T10:00:00Z",
  },
  {
    id: 4002,
    vehicle_id: 1001,
    maintenance_type: "minor",
    category: "轮胎",
    title: "四轮换位",
    maintenance_date: "2025-03-05",
    mileage: 35800,
    cost: 220,
    service_provider: "途虎养车",
    created_at: "2025-03-05T10:00:00Z",
  },
];

export const DEMO_MAINTENANCE_SCHEDULES: MaintenanceSchedule[] = [
  {
    id: 5001,
    vehicle_id: 1001,
    item_name: "机油机滤",
    category: "常规",
    interval_km: 10000,
    interval_days: 365,
    next_due_km: 48420,
    next_due_date: "2026-08-20",
    priority: "medium",
    status: "due",
    created_at: "2023-06-15T08:00:00Z",
    updated_at: new Date(now).toISOString(),
  },
  {
    id: 5002,
    vehicle_id: 1001,
    item_name: "轮胎更换",
    category: "轮胎",
    interval_km: 60000,
    next_due_km: 60000,
    priority: "low",
    status: "pending",
    created_at: "2023-06-15T08:00:00Z",
    updated_at: new Date(now).toISOString(),
  },
];

export const DEMO_LIFECYCLE_EVENTS: LifecycleEvent[] = [
  {
    id: 6001,
    vehicle_id: 1001,
    event_type: "purchase",
    title: "新车交付",
    event_date: "2023-06-15",
    mileage: 0,
    cost: 298000,
    location: "北京·朝阳交付中心",
    created_at: "2023-06-15T08:00:00Z",
  },
  {
    id: 6002,
    vehicle_id: 1001,
    event_type: "maintenance",
    title: "首次保养",
    event_date: "2023-12-10",
    mileage: 5000,
    cost: 0,
    created_at: "2023-12-10T10:00:00Z",
  },
];

export const DEMO_OWNERSHIP: OwnershipRecord[] = [
  {
    id: 7001,
    vehicle_id: 1001,
    owner_name: "当前车主",
    start_date: "2023-06-15",
    transfer_type: "purchase",
    purchase_price: 298000,
    mileage_at_transfer: 0,
    created_at: "2023-06-15T08:00:00Z",
  },
];

export const DEMO_TWIN: DigitalTwin = {
  id: 8001,
  vehicle_id: 1001,
  model_version: "v2.3",
  model_url: "twin://tesla-model-y/1001",
  telemetry: {
    battery_temp: 43.2,
    battery_soc: 68,
    cooling_efficiency: 62,
    cabin_temp: 26,
    tire_pressure_fl: 2.1,
  },
  sync_status: "synced",
  last_sync_at: new Date(now - 60 * 1000).toISOString(),
  sync_frequency: "10s",
  created_at: "2023-06-15T08:00:00Z",
  updated_at: new Date(now).toISOString(),
};

export const DEMO_ARCHIVE: VehicleArchive = {
  vehicle: DEMO_VEHICLE,
  lifecycle_events: DEMO_LIFECYCLE_EVENTS,
  latest_health: DEMO_LATEST_HEALTH,
  health_history: DEMO_HEALTH_HISTORY,
  maintenance_records: DEMO_MAINTENANCE_RECORDS,
  maintenance_schedules: DEMO_MAINTENANCE_SCHEDULES,
  driving_behaviors: DEMO_DRIVING_BEHAVIORS,
  alerts: DEMO_ALERTS,
  ownership_history: DEMO_OWNERSHIP,
  digital_twin: DEMO_TWIN,
  health_score: DEMO_LATEST_HEALTH.health_score,
  active_alert_count: DEMO_ALERTS.filter((a) => a.status === "active").length,
  total_maintenance_cost: 900,
  next_maintenance_items: [{ item_name: "机油机滤", next_due_date: "2026-08-20" }],
};
