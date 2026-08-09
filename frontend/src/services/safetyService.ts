import { get } from "@/utils/request";

/**
 * 合规闸门真实拦截计数客户端。
 *
 * 数据来源：Guardian `GET /api/safety/gate-stats`，由 Guardian 转发 carModel
 * 进程内真实运行时拦截事件的累计计数（见 backend/app/schemas/safety.py）。
 *
 * 诚实数据纪律（前端渲染侧）：
 * - 计数字段为 `number | null`；`null` 表示「取不到」，绝不能渲染成 0。
 * - `source === "unavailable"` 或 `data_status.code !== "ok_carmodel_gate_stats"`
 *   时，整张卡片显示「合规计数暂不可用」，不展示任何数字。
 * - `storage === "memory"` 或 `degraded_reason` 非空时，加注「计数可能不全」。
 */

export type GateSource = "real" | "unavailable";
export type GateStorage = "sqlite" | "memory";

/** 5 类合规闸门类别（对应 carModel `_compliance_hit`）。 */
export type GateCategoryKey =
  | "identity"
  | "geo"
  | "data_fraud"
  | "repair_mislead"
  | "safety_critical";

export type GateDataStatus =
  | "ok_carmodel_gate_stats"
  | "carmodel_unavailable"
  | "carmodel_payload_invalid"
  | (string & {});

export interface GateStatsDataStatus {
  code: GateDataStatus;
  detail?: string;
}

export interface GateStatsResponse {
  total: number | null;
  identity: number | null;
  geo: number | null;
  data_fraud: number | null;
  repair_mislead: number | null;
  /** 注意：safety_critical 的处置是 safety_disclaim（免责引导），并非 refuse 拦截。 */
  safety_critical: number | null;
  source: GateSource;
  /** 最早一次拦截时间（UTC ISO8601）；null 表示至今尚无任何拦截。 */
  since: string | null;
  /** 最近一次拦截时间（UTC ISO8601）。 */
  updated_at: string | null;
  /** sqlite=已落盘可信；memory=进程内降级，重启清零且可能偏小。 */
  storage: GateStorage | null;
  /** 计数链路已知缺陷，非空时 UI 提示该数可能不完整。 */
  degraded_reason: string | null;
  data_status: GateStatsDataStatus;
  /** 真实数据来源端点，便于溯源核对。 */
  data_source: string;
}

export const safetyService = {
  gateStats: () => get<GateStatsResponse>("/api/safety/gate-stats"),
};

export default safetyService;
