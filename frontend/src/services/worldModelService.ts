/**
 * World Model Service — CarSoul 世界模型（carModel）真实接口客户端。
 *
 * 走 Guardian 统一请求层（utils/request）→ Guardian 后端 `/api/carsoul/*`
 * → carModel 引擎。对应关系（见 backend/app/api/carsoul/router.py）：
 *
 *   POST /api/carsoul/simulate        → carModel POST /vehicle/simulate（真实写库）
 *   GET  /api/carsoul/state/{id}      → carModel GET  /world/state/{id}
 *   POST /api/carsoul/predict         → carModel POST /world/predict
 *   POST /api/carsoul/explain         → carModel POST /world/explain
 *   POST /api/carsoul/failure         → carModel POST /world/failure
 *   GET  /api/carsoul/health          → carModel GET  /health
 *
 * 纪律：所有方法都把错误向上抛出，**绝不回落到任何模拟数据**。
 * 后端不可用时由页面渲染显式错误态。
 */
import { get, post } from "@/utils/request";

// ------------------------------------------------------------------
//  Types（与 carModel api/main.py 返回体对齐）
// ------------------------------------------------------------------

/** GET /world/state/{id}：SOH/SOC 为 0-100 量纲（数据库原始值）。 */
export interface WorldState {
  vehicle_id: string;
  basic: {
    brand: string;
    model: string;
    year: number;
    battery_chemistry: string;
  };
  battery: {
    capacity_kwh: number;
    soc: number | null;
    soh: number | null;
    temperature: number | null;
    cycles: number | null;
  };
  driving: { mileage_km: number | null };
  environment: { ambient_temp: number | null };
  as_of: string;
  state_summary: unknown;
  health_embedding: unknown;
}

/** POST /world/predict：current_soh / predicted_soh 为 0-1 量纲。 */
export interface SohPrediction {
  vehicle_id: string;
  current_soh: number;
  predicted_soh: number;
  delta: number;
  risk_level: "low" | "medium" | "high" | (string & {});
  soh_pi95_low: number;
  soh_pi95_high: number;
  sigma_soh: number;
  sigma_source: string;
  /** carModel 明确标注：未做 conformal/分位数校准，勿当严格覆盖率保证。 */
  calibrated: boolean;
  horizon_days: number;
  model_version: string;
  predicted_at: string;
}

export interface ExplainFactor {
  factor: string;
  name: string;
  weight: number;
  evidence: string;
  action: string;
}

/** POST /world/explain：衰减归因 top_factors。 */
export interface DegradationExplain {
  top_factors: ExplainFactor[];
  summary: string;
  concern?: string;
}

/** POST /world/failure：failure_prob 为 0-1 概率，阈值未校准。 */
export interface FailureRisk {
  vehicle_id: string;
  horizon_days: number;
  failure_prob: number;
  risk_level: "low" | "medium" | "high" | (string & {});
  soh_now: number;
  n_history: number;
  model_version: string;
  label_definition: string;
  data_source: string;
  caveat: string;
}

/** POST /vehicle/simulate：真实写库，返回新分配的车辆 ID。 */
export interface SimulateResult {
  generated: number;
  total_profiles: number;
  new_ids: string[];
}

export interface WorldHealth {
  status: string;
  model_version: string;
  now: string;
}

// ------------------------------------------------------------------
//  Service
// ------------------------------------------------------------------
export const worldModelService = {
  /** 世界模型引擎存活检查。 */
  health: () => get<WorldHealth>("/api/carsoul/health"),

  /** 车辆当前数字状态（真实车况快照）。 */
  state: (vehicleId: string) =>
    get<WorldState>(`/api/carsoul/state/${encodeURIComponent(vehicleId)}`),

  /** 未来 horizon_days 天 SOH 预测（需 ≥180 天历史，否则后端 400）。 */
  predict: (vehicleId: string, horizonDays = 90) =>
    post<SohPrediction>("/api/carsoul/predict", {
      vehicle_id: vehicleId,
      horizon_days: horizonDays,
    }),

  /** 衰减归因。 */
  explain: (vehicleId: string, concern = "general") =>
    post<DegradationExplain>("/api/carsoul/explain", {
      vehicle_id: vehicleId,
      concern,
    }),

  /** 未来 horizon_days 天 catastrophic 故障概率。 */
  failure: (vehicleId: string, horizonDays = 90) =>
    post<FailureRisk>("/api/carsoul/failure", {
      vehicle_id: vehicleId,
      horizon_days: horizonDays,
    }),

  /** 生成 N 辆仿真车辆档案 —— 真实写入 carModel 数据库。 */
  simulate: (count = 1, seed = 42) =>
    post<SimulateResult>("/api/carsoul/simulate", { count, seed }),
};

export default worldModelService;
