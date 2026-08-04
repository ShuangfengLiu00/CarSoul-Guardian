import { get, post } from "@/utils/request";

/**
 * 风险预测闭环 — 对接后端 /api/risk/* 与 /api/vehicle/{id}/risk/*。
 *
 * 这一层把"预测 → 确认 → 反馈 → 准确率"的闭环在 UI 上闭合，
 * 让评委能直观看到 Agent 不仅能预测，还能学习（准确率自校准）。
 */

// ------------------------------------------------------------------
//  Types（与后端 schemas/risk_prediction.py 对齐）
// ------------------------------------------------------------------
export interface RiskPrediction {
  id: number;
  vehicle_id: number;
  triggered_by: string;
  is_normal: boolean;
  predicted_level: string;
  predicted_probability: number | null;
  predicted_eta_hours: number | null;
  primary_type: string | null;
  root_cause: string | null;
  trend: string | null;
  explanation: string | null;
  actions_hint: string[] | null;
  anomalies_count: number;
  alert_id: number | null;
  status: string; // open | acknowledged | resolved | expired
  acknowledged_at: string | null;
  actual_outcome: string | null;
  outcome_notes: string | null;
  accuracy: number | null;
  resolved_at: string | null;
  created_at: string;
}

export interface RiskPredictionDetail extends RiskPrediction {
  trace_log: Array<Record<string, unknown>> | null;
}

export interface RiskPredictionList {
  items: RiskPrediction[];
  total: number;
}

export interface RiskAccuracyStats {
  vehicle_id: number;
  total_predictions: number;
  resolved_predictions: number;
  with_feedback: number;
  accurate: number;
  false_alarms: number;
  missed: number;
  accuracy_rate: number | null;
  false_alarm_rate: number | null;
  by_level: Record<string, Record<string, number>>;
}

export interface PatrolSummary {
  patrolled: number;
  predictions_made: number;
  alerts_generated: number;
  details: Array<{
    vehicle_id: number;
    vehicle: string;
    prediction_id: number;
    level: string;
    is_normal: boolean;
    alert_id: number | null;
    status: string;
  }>;
}

export interface SchedulerStatus {
  running: boolean;
  jobs: Array<{
    id: string;
    name: string;
    next_run_time: string | null;
    trigger: string;
  }>;
  config: Record<string, unknown>;
  message: string;
}

export type FeedbackOutcome = "confirmed" | "false_alarm" | "no_event" | "partial";

// ------------------------------------------------------------------
//  Service
// ------------------------------------------------------------------
export const riskService = {
  // 预测历史列表
  listPredictions: (vehicleId: number, status?: string, limit = 50) =>
    get<RiskPredictionList>(
      `/api/vehicle/${vehicleId}/risk/predictions${status ? `?status=${status}` : ""}${limit ? `${status ? "&" : "?"}limit=${limit}` : ""}`,
    ),

  // 单条预测详情（含完整推理轨迹）
  getPrediction: (id: number) =>
    get<RiskPredictionDetail>(`/api/risk/predictions/${id}`),

  // 确认预测（open → acknowledged）
  acknowledge: (id: number) =>
    post<RiskPrediction>(`/api/risk/predictions/${id}/acknowledge`),

  // 提交处置结果（闭合环路）
  submitFeedback: (id: number, actual_outcome: FeedbackOutcome, outcome_notes?: string) =>
    post<RiskPrediction>(`/api/risk/predictions/${id}/feedback`, {
      actual_outcome,
      outcome_notes,
    }),

  // 准确率/误报率统计
  getAccuracy: (vehicleId: number) =>
    get<RiskAccuracyStats>(`/api/vehicle/${vehicleId}/risk/accuracy`),

  // 手动触发单车主预测
  triggerPrediction: (vehicleId: number) =>
    post<RiskPrediction>(`/api/vehicle/${vehicleId}/risk/predict`, { triggered_by: "user" }),

  // 全车主动巡检
  patrol: () => post<PatrolSummary>("/api/risk/patrol"),

  // 调度器状态
  schedulerStatus: () => get<SchedulerStatus>("/api/risk/scheduler/status"),

  // 启动调度器
  schedulerStart: () =>
    post<{ started: boolean } & SchedulerStatus>("/api/risk/scheduler/start"),

  // 停止调度器
  schedulerStop: () =>
    post<{ stopped: boolean } & SchedulerStatus>("/api/risk/scheduler/stop"),
};
