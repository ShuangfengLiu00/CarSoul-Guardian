import { get } from "@/utils/request";

/**
 * 车辆数字生命真实数据客户端。
 *
 * 数据来源：Guardian `GET /api/digital-twin/{vehicleId}/memories` 与
 * `/life-events`，由 SQLAlchemy 直接落盘到 carsoul_dev.db（真实 SQLite，
 * 非前端 Mock）。memories / life-events 经 `generate-lifecycle` 真实生成，
 * 亦可经 `POST /memories`、`POST /life-events` 真实写入。
 *
 * 诚实数据纪律：请求失败或返回空列表时，UI 显示「暂无数据」，绝不回填 Mock。
 */

export interface DigitalTwinMemory {
  id: number;
  vehicle_id: number;
  memory_type: string;
  content: string;
  emotion_score: number | null;
  importance: number;
  source: string;
  meta_data: Record<string, unknown> | null;
  created_time: string;
}

export interface DigitalTwinMemoryList {
  items: DigitalTwinMemory[];
  total: number;
}

export interface DigitalTwinLifeEvent {
  id: number;
  vehicle_id: number;
  event_type: string;
  title: string;
  description: string | null;
  importance: number;
  mileage: number | null;
  location: string | null;
  cost: number | null;
  extra_data: Record<string, unknown> | null;
  event_time: string;
  created_at: string;
}

export interface DigitalTwinLifeEventList {
  items: DigitalTwinLifeEvent[];
  total: number;
}

export const digitalTwinService = {
  getMemories: (vehicleId: number, limit = 50) =>
    get<DigitalTwinMemoryList>(`/api/digital-twin/${vehicleId}/memories?limit=${limit}`),
  getLifeEvents: (vehicleId: number, limit = 50) =>
    get<DigitalTwinLifeEventList>(`/api/digital-twin/${vehicleId}/life-events?limit=${limit}`),
};

export default digitalTwinService;
