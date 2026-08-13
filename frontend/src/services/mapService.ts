import { get } from "@/utils/request";

export interface MapPoi {
  name: string;
  location: string;
  address: string;
  category: string;
  distance: string;
  poi_id: string;
}

export interface MapRoute {
  distance_m: number;
  duration_s: number;
  toll: number;
  steps: number;
}

export interface MapRegeo {
  formatted_address: string;
  province: string;
  city: string;
  district: string;
  street: string;
}

export interface MapStatus {
  provider: string;
  state: "live" | "unavailable";
  reason?: string;
}

export interface MapEnvelope<T> {
  ok: boolean;
  source: "live" | "unavailable";
  provider?: string;
  data?: T;
  error?: string;
}

/** 地图能力（腾讯默认 / 高德备用），经 Guardian /api/map/* 转发 carModel。 */
export const mapService = {
  status: () => get<MapStatus>("/api/map/status"),

  searchPoi: (keyword: string, region?: string, pageSize = 10) =>
    get<MapEnvelope<MapPoi[]>>(
      `/api/map/search-poi?keyword=${encodeURIComponent(keyword)}` +
        `${region ? `&region=${encodeURIComponent(region)}` : ""}&page_size=${pageSize}`,
    ),

  route: (from: string, to: string) =>
    get<MapEnvelope<MapRoute>>(
      `/api/map/route?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`,
    ),

  regeo: (location: string) =>
    get<MapEnvelope<MapRegeo>>(
      `/api/map/regeo?location=${encodeURIComponent(location)}`,
    ),
};
