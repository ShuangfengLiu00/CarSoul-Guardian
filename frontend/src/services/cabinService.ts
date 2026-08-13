import { get, post } from "@/utils/request";

export interface CabinCard {
  id: string;
  title: string;
  detail: string;
  level: "info" | "warning" | "success";
}

export interface CabinSuggestions {
  vehicle_id: string;
  scene: { time_of_day?: string; speed_kmh?: number; occupancy?: number };
  vehicle_state?: { soc?: number | null; temp?: number | null };
  cards: CabinCard[];
  control_redline?: string;
  note?: string;
}

/** 座舱陪伴（AGT-205）：场景建议卡片 + 长期偏好记忆，经 Guardian /api/cabin/* 转发 carModel。 */
export const cabinService = {
  suggestions: (vehicleId: string, opts?: { time_of_day?: string; speed_kmh?: number; occupancy?: number }) => {
    const p = new URLSearchParams({ vehicle_id: vehicleId, occupancy: String(opts?.occupancy ?? 1) });
    if (opts?.time_of_day) p.set("time_of_day", opts.time_of_day);
    if (opts?.speed_kmh != null) p.set("speed_kmh", String(opts.speed_kmh));
    return get<CabinSuggestions>(`/api/cabin/suggestions?${p.toString()}`);
  },

  getPreferences: (vehicleId: string) =>
    get<{ vehicle_id: string; preferences: Record<string, unknown>; note?: string }>(
      `/api/cabin/preferences?vehicle_id=${encodeURIComponent(vehicleId)}`,
    ),

  setPreferences: (vehicleId: string, preferences: Record<string, unknown>) =>
    post<{ vehicle_id: string; saved: boolean; preferences: Record<string, unknown> }>("/api/cabin/preferences", {
      vehicle_id: vehicleId,
      preferences,
    }),
};
