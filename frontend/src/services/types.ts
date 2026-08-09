/** Shared API types for CarSoul Guardian frontend (TASK007). */

// ---- User ----
export interface UserOut {
  id: number;
  username: string;
  email: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  username?: string;
}

// ---- Vehicle ----
export interface Vehicle {
  id: number;
  owner_id?: number;
  brand: string;
  model: string;
  year: number;
  vin: string;
  plate_number?: string;
  color?: string;
  nickname?: string;
  engine_type?: string;
  fuel_type: string;
  displacement?: number;
  battery_capacity?: number;
  mileage: number;
  status: string;
  purchase_date?: string;
  purchase_price?: number;
  dealer?: string;
  insurance_company?: string;
  insurance_policy_no?: string;
  insurance_expiry?: string;
  registration_date?: string;
  inspection_expiry?: string;
  twin_model_id?: string;
  twin_last_sync?: string;
  avatar_url?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface VehicleList {
  items: Vehicle[];
  total: number;
}

// ---- Lifecycle Events ----
export interface LifecycleEvent {
  id: number;
  vehicle_id: number;
  event_type: string;
  title: string;
  description?: string;
  event_date: string;
  mileage?: number;
  cost?: number;
  location?: string;
  severity?: string;
  extra_data?: Record<string, unknown>;
  created_at: string;
}

export interface LifecycleEventList {
  items: LifecycleEvent[];
  total: number;
}

// ---- Health ----
export interface HealthItem {
  id: number;
  snapshot_id: number;
  vehicle_id: number;
  category: string;
  item_name: string;
  level: string;
  score?: number;
  detail?: string;
  recommendation?: string;
}

export interface HealthSnapshot {
  id: number;
  vehicle_id: number;
  health_score: number;
  mileage: number;
  engine_score?: number;
  brake_score?: number;
  tire_score?: number;
  battery_score?: number;
  body_score?: number;
  electronics_score?: number;
  summary?: string;
  source: string;
  snapshot_time: string;
  items: HealthItem[];
}

export interface HealthSnapshotList {
  items: HealthSnapshot[];
  total: number;
}

// ---- Maintenance ----
export interface MaintenanceRecord {
  id: number;
  vehicle_id: number;
  maintenance_type: string;
  category: string;
  title: string;
  description?: string;
  maintenance_date: string;
  mileage?: number;
  cost?: number;
  service_provider?: string;
  technician?: string;
  parts?: Array<Record<string, unknown>>;
  next_maintenance_date?: string;
  next_maintenance_mileage?: number;
  created_at: string;
}

export interface MaintenanceRecordList {
  items: MaintenanceRecord[];
  total: number;
}

export interface MaintenanceSchedule {
  id: number;
  vehicle_id: number;
  item_name: string;
  category: string;
  interval_km?: number;
  interval_days?: number;
  last_mileage?: number;
  last_date?: string;
  next_due_km?: number;
  next_due_date?: string;
  priority: string;
  status: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface MaintenanceScheduleList {
  items: MaintenanceSchedule[];
  total: number;
}

// ---- Driving Behavior ----
export interface DrivingBehavior {
  id: number;
  vehicle_id: number;
  record_date: string;
  trip_count: number;
  total_distance: number;
  total_duration: number;
  avg_speed?: number;
  max_speed?: number;
  safety_score?: number;
  eco_score?: number;
  harsh_acceleration_count: number;
  harsh_braking_count: number;
  sharp_turn_count: number;
  overspeed_count: number;
  idle_duration: number;
  fuel_consumption?: number;
  energy_efficiency?: number;
  created_at: string;
}

export interface DrivingBehaviorList {
  items: DrivingBehavior[];
  total: number;
}

export interface DrivingBehaviorSummary {
  total_distance: number;
  total_duration: number;
  avg_safety_score?: number;
  avg_eco_score?: number;
  total_harsh_events: number;
  total_fuel: number;
  trip_count: number;
}

// ---- Alerts ----
export interface Alert {
  id: number;
  vehicle_id: number;
  alert_type: string;
  level: string;
  category?: string;
  title: string;
  detail?: string;
  recommendation?: string;
  status: string;
  acknowledged_at?: string;
  resolved_at?: string;
  triggered_at: string;
}

export interface AlertList {
  items: Alert[];
  total: number;
}

// ---- Ownership ----
export interface OwnershipRecord {
  id: number;
  vehicle_id: number;
  owner_id?: number;
  owner_name?: string;
  start_date: string;
  end_date?: string;
  transfer_type: string;
  purchase_price?: number;
  sale_price?: number;
  mileage_at_transfer?: number;
  notes?: string;
  created_at: string;
}

export interface OwnershipRecordList {
  items: OwnershipRecord[];
  total: number;
}

// ---- Digital Twin ----
export interface DigitalTwin {
  id: number;
  vehicle_id: number;
  model_version: string;
  model_url?: string;
  telemetry?: Record<string, unknown>;
  config?: Record<string, unknown>;
  sync_status: string;
  last_sync_at?: string;
  sync_frequency: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

// ---- Sensor Data (IoT telemetry) ----
export interface SensorData {
  id: number;
  vehicle_id: number;
  sensor_type: string;
  sensor_value: number;
  unit?: string;
  meta?: Record<string, unknown>;
  created_at: string;
}

export interface SensorDataList {
  items: SensorData[];
  total: number;
}

export interface SensorSeriesPoint {
  timestamp: string;
  value: number;
}

export interface SensorSeries {
  sensor_type: string;
  unit?: string;
  points: SensorSeriesPoint[];
}

// ---- Full-vehicle sensor snapshot (6 domains / 58 signals) ----
// 对应后端 backend/app/schemas/sensor_data.py 的 SensorSnapshotResponse。

/** 单个传感器的 registry 静态元数据：量程、告警阈值、采样率。 */
export interface SensorSpecOut {
  min?: number;
  max?: number;
  warn_low?: number | null;
  warn_high?: number | null;
  crit_low?: number | null;
  crit_high?: number | null;
  step?: number;
  sample_hz_can?: number;
  sample_hz_upload?: number;
  adjustable?: boolean;
}

export type SensorStatus = "normal" | "warn" | "crit";

/** 单个传感器的当前值 + spec + 派生状态。 */
export interface SensorSnapshotSensor {
  sensor_type: string;
  label: string;
  value: number;
  unit?: string | null;
  spec: SensorSpecOut | null;
  status: SensorStatus;
  /** seed（库内读数）| default（registry 基线回落） */
  source: string;
}

/** 一个传感器域及其信号。 */
export interface SensorSnapshotDomain {
  domain: string;
  label: string;
  vhs_component?: string;
  vhs_weight?: number;
  sensors: SensorSnapshotSensor[];
}

/** 自包含的简化 VHS 基线分。 */
export interface SensorSnapshotBaseline {
  health_score: number;
  grade: string;
  grade_label: string;
  /** domain key → 域得分 */
  breakdown: Record<string, number>;
}

/** GOAI 数据来源溯源信封。 */
export interface SensorSnapshotProvenance {
  data_source: string;
  demo_mode: boolean;
  badge_level: string;
  origin: string;
  as_of: string;
}

export interface SensorSnapshot {
  vehicle_id: number;
  as_of: string;
  energy_type: string;
  domains: SensorSnapshotDomain[];
  baseline: SensorSnapshotBaseline;
  provenance: SensorSnapshotProvenance;
}

// ---- Trips ----
export interface Trip {
  id: number;
  vehicle_id: number;
  driver_id?: number;
  start_time: string;
  end_time?: string;
  distance: number;
  average_speed?: number;
  max_speed?: number;
  energy_consumption?: number;
  road_condition?: string;
  weather?: string;
  harsh_acceleration_count: number;
  harsh_braking_count: number;
  overspeed_count: number;
  start_location?: Record<string, unknown>;
  end_location?: Record<string, unknown>;
  notes?: string;
  created_at: string;
}

export interface TripList {
  items: Trip[];
  total: number;
}

export interface TripSummary {
  trip_count: number;
  total_distance: number;
  total_duration_hours: number;
  total_energy: number;
  avg_speed?: number;
  harsh_events: number;
  first_trip_time?: string;
  last_trip_time?: string;
}

// ---- Fault Logs (vehicle disease history) ----
export interface FaultLog {
  id: number;
  vehicle_id: number;
  fault_code: string;
  fault_level: string; // low | medium | high | critical
  description?: string;
  system?: string;
  repair_status: string; // active | diagnosing | repairing | resolved | ignored
  mileage?: number;
  occur_time: string;
  resolved_time?: string;
  maintenance_record_id?: number;
  created_at: string;
}

export interface FaultLogList {
  items: FaultLog[];
  total: number;
}

// ---- Digital State (real-time) ----
export interface DigitalState {
  id: number;
  vehicle_id: number;
  engine_health?: number;
  battery_health?: number;
  brake_health?: number;
  tire_health?: number;
  body_health?: number;
  electronics_health?: number;
  overall_score?: number;
  status: string; // GOOD | WARNING | DANGER | END_OF_LIFE
  temperature?: number;
  mileage?: number;
  fuel_level?: number;
  location?: Record<string, unknown>;
  updated_at: string;
  created_at: string;
}

// ---- Vehicle Health Score (VHS) ----
export interface HealthScoreBreakdown {
  engine: number;
  battery: number;
  chassis: number;
  driving: number;
  maintenance: number;
  engine_contribution: number;
  battery_contribution: number;
  chassis_contribution: number;
  driving_contribution: number;
  maintenance_contribution: number;
}

export interface VehicleHealthScore {
  vehicle_id: number;
  score: number;
  grade: string; // golden | excellent | fair | risk
  grade_label: string; // 黄金车况 | 优秀 | 一般 | 风险车辆
  breakdown: HealthScoreBreakdown;
  weights: Record<string, number>;
  computed_at: string;
}

// ---- Vehicle Digital Life Record (flagship) ----
export interface VehicleIdentity {
  vehicle_id: number;
  digital_identity: string; // VX-YYYY-NNNNN
  name: string;
  brand: string;
  model: string;
  year: number;
  vin: string;
  energy_type: string;
  color?: string;
  nickname?: string;
  avatar_url?: string;
}

export interface LifeEventItem {
  date: string;
  event_type: string;
  title: string;
  description?: string;
  mileage?: number;
  cost?: number;
  icon?: string;
}

export interface PredictionItem {
  component: string;
  current_health?: number;
  predicted_failure_date?: string;
  risk_level: string; // low | medium | high
  reason: string;
  suggestion?: string;
}

export interface VehicleLifeRecord {
  identity: VehicleIdentity;
  health_score?: number;
  health_grade?: string;
  health_grade_label?: string;
  status: string; // GOOD | WARNING | DANGER | END_OF_LIFE
  status_label: string;
  age_years: number;
  age_label: string;
  mileage: number;
  mileage_label: string;
  predicted_lifespan_years?: number;
  predicted_remaining_years?: number;
  predicted_lifespan_label?: string;
  today_temperature?: number;
  today_fuel_level?: number;
  today_location?: Record<string, unknown>;
  engine_health?: number;
  battery_health?: number;
  brake_health?: number;
  tire_health?: number;
  health_breakdown?: HealthScoreBreakdown;
  life_events: LifeEventItem[];
  predictions: PredictionItem[];
  ai_suggestions: string[];
  total_trips: number;
  total_maintenance_cost: number;
  fault_count: number;
  active_fault_count: number;
  ai_doctor_enabled: boolean;
  personality?: Record<string, unknown>;
}

// ---- Simulation (mock data generator) ----
export interface SimulationRequest {
  vehicle_id?: number;
  sensor_points?: number;
  trip_count?: number;
  fault_count?: number;
  days?: number;
  update_digital_state?: boolean;
}

export interface SimulationResult {
  vehicle_id: number;
  sensor_data_created: number;
  trips_created: number;
  faults_created: number;
  digital_state_updated: boolean;
  message: string;
}

// ---- Service Orders (after-sales closed loop — §3A.1) ----
export interface ServiceOrderStatusHistoryEntry {
  status: string;
  timestamp: string;
  note?: string;
}

export interface ServiceOrder {
  id: number;
  vehicle_id: number;
  service_type: string;
  service_name: string;
  priority: string;
  reason: string;
  description?: string | null;
  service_provider?: string | null;
  estimated_response?: string | null;
  diagnosis_summary?: string | null;
  status: string;
  booked_at?: string | null;
  in_service_at?: string | null;
  done_at?: string | null;
  closed_at?: string | null;
  status_history: ServiceOrderStatusHistoryEntry[];
  cost?: number | null;
  feedback_type?: string | null;
  feedback_note?: string | null;
  feedback_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ServiceOrderList {
  items: ServiceOrder[];
  total: number;
}

export interface ServiceOrderCreate {
  service_type: string;
  service_name: string;
  priority: string;
  reason: string;
  description?: string;
  service_provider?: string;
  estimated_response?: string;
  diagnosis_summary?: string;
}

export interface ServiceOrderUpdate {
  status?: string;
  note?: string;
  service_provider?: string;
  estimated_response?: string;
  cost?: number;
}

export interface ServiceOrderFeedback {
  feedback_type: string;
  feedback_note?: string;
}

// ---- Archive (aggregated) ----
export interface VehicleArchive {
  vehicle: Vehicle;
  lifecycle_events: LifecycleEvent[];
  latest_health: HealthSnapshot | null;
  health_history: HealthSnapshot[];
  maintenance_records: MaintenanceRecord[];
  maintenance_schedules: MaintenanceSchedule[];
  driving_behaviors: DrivingBehavior[];
  alerts: Alert[];
  ownership_history: OwnershipRecord[];
  digital_twin: DigitalTwin | null;
  health_score: number | null;
  active_alert_count: number;
  total_maintenance_cost: number;
  next_maintenance_items: Array<Record<string, unknown>>;
}

// ---- Agent ----
export interface AgentChatRequest {
  user: string;
  message: string;
  session_id?: string;
}

/** 守护闭环单步(感知→诊断→风险→建议→执行) */
export interface ClosedLoopStep {
  step: string;
  agent: string;
  title: string;
  detail: string;
  status: string;
  data?: Record<string, unknown>;
}

/** 守护闭环摘要:CarSoul 五子 Agent 工作流的结构化输出 */
export interface ClosedLoop {
  is_normal: boolean;
  steps: ClosedLoopStep[];
  anomalies: Array<Record<string, unknown>>;
  expert_opinions?: Array<Record<string, unknown>>;
  diagnosis: Record<string, unknown>;
  risk: Record<string, unknown>;
  actions: string[];
  reminder?: { title?: string; level?: string; [k: string]: unknown } | null;
  escalation?: Record<string, unknown> | null;
  trip_context?: TripContext | null;
  knowledge_retrieval?: KnowledgeRetrieval | null;
  trip_report?: TripReport | null;
  // V1.0: Governance + Workflow Engine outputs
  judge_verdict?: JudgeVerdict | null;
  workflow_meta?: WorkflowMeta | null;
}

/** Judge Agent 仲裁结果 */
export interface JudgeVerdict {
  verdict: string; // consensus | conflict_resolved | insufficient_data
  primary_cause: string | null;
  primary_type?: string;
  primary_specialty?: string;
  confidence: number;
  contributor_weights: Record<string, number>;
  conflict_detected: boolean;
  root_causes_seen?: string[];
  severities_seen?: string[];
  reasoning: string;
}

/** 工作流引擎元数据 */
export interface WorkflowMeta {
  workflow_id: string;
  intent: {
    goal: string;
    goal_label: string;
    vehicle_id: string;
    priority: string;
    scenario: string;
    raw_message: string;
    detected_keywords: string[];
    trip_distance_km: number | null;
  };
  task_tree: {
    root_goal: string;
    task_count: number;
    tasks: Array<{
      task_id: string;
      name: string;
      task_type: string;
      agent_id: string;
      dependencies: string[];
      parallel_group: string | null;
      priority: number;
      state: string;
      error: string | null;
      retry_count: number;
      max_retries: number;
    }>;
  };
  state_machine: {
    workflow_id: string;
    state: string;
    retry_count: number;
    started_at: string;
    transitions: number;
  };
  memory: {
    workflow_id: string;
    goal: string;
    created_at: string;
    completed_at: string | null;
    participating_agents: string[];
    final_conclusion: Record<string, unknown>;
    agent_performance: Record<string, unknown>;
  };
  governance: {
    agent_count: number;
    active_count: number;
    agents: Array<Record<string, unknown>>;
  };
}

/** 长途出行场景上下文 */
export interface TripContext {
  is_long_trip: boolean;
  distance_km: number;
  trip_type: string;
  estimated_hours: number;
  charging_stops_needed: number;
  message?: string;
}

/** RAG 知识检索详情（用于闭环可视化） */
export interface KnowledgeChunkInfo {
  title: string;
  heading: string;
  score: number;
  preview: string;
}

export interface KnowledgeRetrieval {
  query: string;
  chunk_count: number;
  sources: string[];
  chunks: KnowledgeChunkInfo[];
}

/** 结构化出行健康报告 */
export interface TripProblem {
  item: string;
  value: string;
  threshold: string;
  severity: string;
  detail: string;
}

export interface TripReport {
  title: string;
  risk_level: string;
  risk_color: string;
  risk_probability: number;
  distance_km: number;
  estimated_hours: number;
  problems: TripProblem[];
  root_cause: string;
  knowledge_match?: string;
  impact: string;
  recommendations: string[];
  charging_plan: {
    stops: number;
    interval_km: number;
    strategy: string;
  };
  knowledge_sources: string[];
  verdict: string;
}

export interface AgentCitation {
  id?: string;
  title?: string;
  source?: string;
  source_type?: string;
  confidence?: string;
  needs_verification?: boolean;
  category?: string;
  score?: number;
  [k: string]: unknown;
}

export interface AgentDegraded {
  reason: string;
  detail?: string;
  impact?: string;
  /**
   * 本轮回答是否**真的**因大模型链路不可用而受损。
   *
   * 与"degraded 非空"是两个正交事实：degraded 非空只说明**链路**不可用
   * （llm_available=false），而合规拒答 / OOD 声明 / 信息不足反问这些确定性
   * 路径本就不经大模型，链路挂了它们的输出也不变 → affects_this_turn=false。
   *
   * **判降级只能用 `degraded?.affects_this_turn === true`**。用"degraded 非空"
   * 会把一次正常的合规拒答显示成「降级模式」，那是凭空制造一个不存在的缺陷。
   */
  affects_this_turn?: boolean;
  [k: string]: unknown;
}

export interface AgentChatResponse {
  answer: string;
  /** "active" 仅当 llm_available && llm_used，其余一律 "degraded"。上游必填。 */
  agent_status: string;
  session_id?: string;
  agent_name: string;
  closed_loop?: ClosedLoop | null;
  /** 本轮 LLM 链路是否真的可用（不是"环境变量配没配"） */
  llm_available?: boolean;
  /** 本轮是否真的调用了 LLM。与 llm_available 正交，不可合并 */
  llm_used?: boolean;
  degraded?: AgentDegraded | null;
  citations?: AgentCitation[];
  /** 是否被合规闸门**拒答**。safety_critical 类不拒答，此值为 false。 */
  compliance_refused?: boolean;
  /**
   * 合规闸门命中类别：geo / identity / data_fraud / repair_mislead / safety_critical。
   * **非空即代表闸门介入过** —— 判断"闸门是否生效"只能看这个，
   * 只看 compliance_refused 会漏掉 safety_critical 一整类。
   */
  compliance_category?: string | null;
  /** refuse=直接拒答；safety_disclaim=免责并导向专业检修（不是拒答）；null=未命中闸门 */
  compliance_action?: string | null;
  /**
   * 答案中是否检出并移除了无工具证据的安全结论（安全时限/磨损到极限/立即停驶）。
   * false 仅表示未命中这三类模式，**不等于**答案已被证明安全。
   */
  safety_scrubbed?: boolean;
  /** 被移除的编造安全结论片段，便于溯源 */
  safety_scrub_hits?: unknown[];
  model_version?: string | null;
  /** carmodel_agent_chat / local_agent / offline_fallback */
  engine?: string;
}

export interface AlertItem {
  level: "info" | "warning" | "critical";
  title: string;
  detail: string;
  /** 该条告警的数据来源（如 carmodel:/world/state），便于溯源 */
  source?: string | null;
}

/** 本次 overview 的数据真实性说明。UI 必须据此决定显示真值还是「暂无数据」。 */
export interface HealthDataStatus {
  /** ok_carmodel_state | no_vehicle_selected | carmodel_unavailable | carmodel_state_incomplete */
  code: string;
  detail: string;
}

/**
 * 最近一次真实观测到的大模型链路状态。
 * agent_status 只有三档，分不清"链路挂了导致回答变差"和"链路挂了但这轮是
 * 合规拒答、回答本就不该经大模型"。这里把两个正交事实分开给 UI。
 */
export interface AgentLinkState {
  llm_available: boolean;
  llm_used: boolean;
  /** 最近一轮回答是否**真的**受损（= degraded.affects_this_turn）。
   *  - false = 确证未受损（确定性路径：合规闸门 / 反问 / 超纲声明）
   *  - true  = 确证受损（真降级）
   *  - null  = 未证明（上游违约：llm_available=false 却没给 degraded）。
   *    此时不许当作 false——没证明没受损就不许当没受损，必须按受损处理。 */
  affects_last_turn: boolean | null;
  engine: string;
  reason?: string | null;
  /** 为 null/缺省表示尚未发生过任何一轮对话 */
  observed_at?: string | null;
}

export interface HealthOverview {
  /**
   * 0-100 综合健康分。**null = 取不到真实车况**。
   * 绝不能在 UI 里用 `?? 0` 或演示数据兜底把它变成一个好看的数字 ——
   * 历史版本后端硬编码 92，那正是要根除的东西。
   */
  health_score: number | null;
  /** 健康分的来源与口径，便于用户判断这个数字可不可信 */
  health_score_basis?: string | null;
  agent_status: string;
  /** null = 尚未观测过任何一轮对话（与"观测到不可用"不是一回事） */
  agent_link?: AgentLinkState | null;
  recent_alerts: AlertItem[];
  vehicle_id?: string | null;
  /** 车况数据在 carModel 侧的观测时间 */
  as_of?: string | null;
  data_source?: string | null;
  data_status: HealthDataStatus;
}

// ---- Knowledge Base (RAG) ----
export interface KnowledgeChunk {
  title: string;
  heading: string;
  category: string;
  source: string;
  score: number;
  backend: string;
  text: string;
}

export interface KnowledgeSearchRequest {
  query: string;
  top_k?: number;
}

export interface KnowledgeSearchResponse {
  query: string;
  results: KnowledgeChunk[];
  count: number;
  context: string;
  stats: Record<string, unknown>;
}

export interface KnowledgeIngestRequest {
  title: string;
  category: string;
  content: string;
  source?: string;
}

export interface KnowledgeIngestResponse {
  title: string;
  chunks_added: number;
  total_chunks: number;
  message: string;
}

export interface KnowledgeStats {
  chunk_count: number;
  backend: string;
  embedder: string;
  docs_dir: string;
  ready: boolean;
}

// ===========================================================================
// TASK007-V2: Vehicle Digital Life Engine (数字生命引擎)
// ===========================================================================

// ---- Digital Life Identity (数字身份 — TASK007-V2) ----
export interface DigitalLifeIdentity {
  id: number;
  vehicle_id: number;
  vehicle_uuid: string;
  vin?: string;
  brand?: string;
  model?: string;
  production_year?: number;
  energy_type?: string;
  vehicle_class?: string;
  owner_id?: number;
  birth_time?: string;
  nickname?: string;
  created_at: string;
}

// ---- Vehicle Life State (生命状态) ----
export interface VehicleLifeState {
  id: number;
  vehicle_id: number;
  health_score?: number;
  life_stage: string; // NEW | GROWTH | MATURE | AGING | RETIRE
  mileage: number;
  vehicle_age_days: number;
  energy_health?: number;
  mechanical_health?: number;
  software_health?: number;
  soul_score?: number;
  updated_at: string;
}

// ---- Vehicle Health Metrics (细分健康) ----
export interface VehicleHealthMetric {
  id: number;
  vehicle_id: number;
  component: string;
  health_score?: number;
  temperature?: number;
  wear_level?: number;
  risk_level: string;
  record_time: string;
}

export interface VehicleHealthMetricList {
  items: VehicleHealthMetric[];
  total: number;
}

// ---- Vehicle Life Event (生命事件) ----
export interface VehicleLifeEventItem {
  id: number;
  vehicle_id: number;
  event_type: string;
  title: string;
  description?: string;
  importance: number;
  mileage?: number;
  location?: string;
  cost?: number;
  extra_data?: Record<string, unknown>;
  event_time: string;
  created_at: string;
}

export interface VehicleLifeEventList {
  items: VehicleLifeEventItem[];
  total: number;
}

// ---- Vehicle Memory (记忆系统) ----
export interface VehicleMemoryItem {
  id: number;
  vehicle_id: number;
  memory_type: string;
  content: string;
  emotion_score?: number;
  importance: number;
  source: string;
  meta_data?: Record<string, unknown>;
  created_time: string;
}

export interface VehicleMemoryList {
  items: VehicleMemoryItem[];
  total: number;
}

// ---- Driver Profile (驾驶人格) ----
export interface DriverProfile {
  id: number;
  vehicle_id: number;
  driver_style: string;
  aggressive_score?: number;
  comfort_score?: number;
  eco_score?: number;
  total_trips: number;
  total_distance: number;
  total_duration: number;
  total_harsh_events: number;
  preferred_speed_range?: string;
  preferred_driving_time?: string;
  preferred_road_type?: string;
  updated_at: string;
}

// ---- Vehicle Prediction (AI预测) ----
export interface VehiclePredictionItem {
  id: number;
  vehicle_id: number;
  target_component: string;
  prediction: string;
  risk_level: string;
  confidence?: number;
  predicted_value?: number;
  predicted_unit?: string;
  predicted_time?: string;
  root_cause?: string;
  suggestion?: string;
  status: string;
  actual_outcome?: string;
  prediction_time: string;
  created_at: string;
}

export interface VehiclePredictionList {
  items: VehiclePredictionItem[];
  total: number;
}

// ---- Vehicle Soul Score (VSS 灵魂指数) ----
export interface SoulScoreBreakdown {
  health: number;
  memory: number;
  maintenance: number;
  driving: number;
  prediction: number;
  health_contribution: number;
  memory_contribution: number;
  maintenance_contribution: number;
  driving_contribution: number;
  prediction_contribution: number;
}

export interface VehicleSoulScore {
  vehicle_id: number;
  soul_id: string;
  score: number;
  grade: string; // legendary | excellent | normal | risk
  grade_label: string;
  breakdown: SoulScoreBreakdown;
  computed_at: string;
}

export interface VehicleSoulScoreHistoryItem {
  id: number;
  vehicle_id: number;
  soul_score: number;
  health_score?: number;
  memory_score?: number;
  maintenance_score?: number;
  driving_score?: number;
  prediction_score?: number;
  grade?: string;
  notes?: string;
  recorded_at: string;
}

export interface VehicleSoulScoreHistoryList {
  items: VehicleSoulScoreHistoryItem[];
  total: number;
}

// ---- Soul Profile (灵魂档案聚合视图) ----
export interface SoulProfile {
  soul_id: string;
  vehicle_id: number;
  name: string;
  brand: string;
  model: string;
  year?: number;
  energy_type: string;
  nickname?: string;

  soul_score: number;
  soul_grade: string;
  soul_grade_label: string;
  soul_breakdown: SoulScoreBreakdown;

  life_stage: string;
  life_stage_label: string;
  health_score?: number;
  energy_health?: number;
  mechanical_health?: number;
  software_health?: number;

  companion_days: number;
  mileage: number;
  mileage_label: string;

  life_events: VehicleLifeEventItem[];
  life_events_count: number;

  memories: VehicleMemoryItem[];
  memories_count: number;

  health_metrics: VehicleHealthMetric[];

  predictions: VehiclePredictionItem[];

  driver_profile?: DriverProfile;
  driver_style_label: string;

  ai_insights: string[];

  agent_hooks: Record<string, { status: string; endpoint: string }>;
}

// ---- Create Digital Life Response ----
export interface CreateDigitalLifeResponse {
  vehicle_id: number;
  soul_id: string;
  message: string;
  identity: DigitalLifeIdentity;
}

// ---- Agent Query ----
export interface AgentQueryRequest {
  query: string;
  agent_type: string;
  context?: Record<string, unknown>;
}

export interface AgentQueryResponse {
  agent_type: string;
  answer: string;
  confidence?: number;
  suggestions: string[];
  data?: Record<string, unknown>;
}

// ---- Lifecycle Generation Result ----
export interface LifecycleGenerationResult {
  vehicle_id: number;
  message: string;
  days?: number;
  health_metrics?: number;
  sensor_readings?: number;
  life_events?: number;
  memories?: number;
  predictions?: number;
  total_mileage?: number;
  total_trips?: number;
  total_distance?: number;
  total_harsh_events?: number;
  skipped?: boolean;
}
