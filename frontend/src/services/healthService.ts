import { get } from "@/utils/request";
import type { HealthOverview } from "./types";

export const healthService = {
  /**
   * Dashboard 概览。
   *
   * `vehicleId` 是 **carModel 侧**的 vehicle_id（如 CS001），不是 Guardian 的
   * 数字主键 —— 两者目前没有映射关系。不传则由后端回落到
   * CARSOUL_WORLD_DEFAULT_VEHICLE_ID；若那也没配，后端会如实返回
   * `health_score: null` + `data_status.code = "no_vehicle_selected"`。
   */
  overview: (vehicleId?: string) =>
    get<HealthOverview>(
      "/api/health/overview",
      vehicleId ? { params: { vehicle_id: vehicleId } } : undefined,
    ),
};
