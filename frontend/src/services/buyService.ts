import { get, post } from "@/utils/request";

export interface BuyVehicle {
  brand: string;
  model: string;
  chemistry: string;
  capacity_kwh: number;
  year_min: number;
  range_km: number;
  value_score: number;
  chem_note?: string;
  score?: number;
}

export interface RecommendFilters {
  budget?: number | null;
  chemistry?: string | null;
  purpose?: string | null;
}

/** 购车顾问（AGT-209）：车型推荐 / 配置对比，经 Guardian /api/buy/* 转发 carModel。 */
export const buyService = {
  catalog: () => get<{ items: BuyVehicle[]; total: number; note?: string }>("/api/buy/catalog"),

  recommend: (body: {
    max_budget?: number | null;
    preferred_chemistry?: string | null;
    purpose?: string | null;
    top_k?: number;
  }) => post<{ items: BuyVehicle[]; filters: RecommendFilters; note?: string; budget_note?: string }>("/api/buy/recommend", body),

  compare: (a: string, b: string) =>
    get<{ a: BuyVehicle; b: BuyVehicle; keys: string[]; note?: string }>(
      `/api/buy/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`,
    ),
};
