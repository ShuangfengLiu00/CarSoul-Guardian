import { get, post } from "@/utils/request";
import type {
  SoulProfile,
  VehicleSoulScore,
  VehicleSoulScoreHistoryList,
  VehicleLifeState,
  VehicleLifeEventList,
  VehicleLifeEventItem,
  VehicleMemoryList,
  VehicleMemoryItem,
  VehicleHealthMetricList,
  VehicleHealthMetric,
  VehiclePredictionList,
  VehiclePredictionItem,
  DriverProfile,
  CreateDigitalLifeResponse,
  AgentQueryRequest,
  AgentQueryResponse,
  LifecycleGenerationResult,
} from "./types";

export const soulService = {
  // ---- Create Digital Life ----
  createDigitalLife: (vehicleId: number) =>
    post<CreateDigitalLifeResponse>(`/api/digital-twin/create?vehicle_id=${vehicleId}`, {}),

  // ---- Soul Profile (旗舰读模型) ----
  getSoulProfile: (vehicleId: number) =>
    get<SoulProfile>(`/api/digital-twin/${vehicleId}/profile`),

  // ---- Soul Score (VSS) ----
  getSoulScore: (vehicleId: number) =>
    get<VehicleSoulScore>(`/api/digital-twin/${vehicleId}/soul-score`),

  // ---- Soul Score History ----
  getSoulHistory: (vehicleId: number, limit = 30) =>
    get<VehicleSoulScoreHistoryList>(`/api/digital-twin/${vehicleId}/soul-history?limit=${limit}`),

  // ---- Life State ----
  getLifeState: (vehicleId: number) =>
    get<VehicleLifeState>(`/api/digital-twin/${vehicleId}/life-state`),

  refreshLifeState: (vehicleId: number) =>
    post<VehicleLifeState>(`/api/digital-twin/${vehicleId}/life-state/refresh`, {}),

  // ---- Life Events ----
  listLifeEvents: (vehicleId: number, eventType?: string, limit = 50) =>
    get<VehicleLifeEventList>(
      `/api/digital-twin/${vehicleId}/life-events${eventType ? `?event_type=${eventType}&` : "?"}limit=${limit}`,
    ),
  createLifeEvent: (vehicleId: number, body: Partial<VehicleLifeEventItem>) =>
    post<VehicleLifeEventItem>(`/api/digital-twin/${vehicleId}/life-events`, body),

  // ---- Memories ----
  listMemories: (vehicleId: number, memoryType?: string, limit = 50) =>
    get<VehicleMemoryList>(
      `/api/digital-twin/${vehicleId}/memories${memoryType ? `?memory_type=${memoryType}&` : "?"}limit=${limit}`,
    ),
  createMemory: (vehicleId: number, body: Partial<VehicleMemoryItem>) =>
    post<VehicleMemoryItem>(`/api/digital-twin/${vehicleId}/memories`, body),
  searchMemories: (vehicleId: number, query: string) =>
    get<VehicleMemoryList>(`/api/digital-twin/${vehicleId}/memories/search?q=${encodeURIComponent(query)}`),

  // ---- Health Metrics ----
  listHealthMetrics: (vehicleId: number, component?: string, limit = 50) =>
    get<VehicleHealthMetricList>(
      `/api/digital-twin/${vehicleId}/health-metrics${component ? `?component=${component}&` : "?"}limit=${limit}`,
    ),
  createHealthMetric: (vehicleId: number, body: Partial<VehicleHealthMetric>) =>
    post<VehicleHealthMetric>(`/api/digital-twin/${vehicleId}/health-metrics`, body),

  // ---- Predictions ----
  listPredictions: (vehicleId: number, status?: string, limit = 20) =>
    get<VehiclePredictionList>(
      `/api/digital-twin/${vehicleId}/predictions${status ? `?status=${status}&` : "?"}limit=${limit}`,
    ),
  createPrediction: (vehicleId: number, body: Partial<VehiclePredictionItem>) =>
    post<VehiclePredictionItem>(`/api/digital-twin/${vehicleId}/predictions`, body),

  // ---- Driver Profile ----
  getDriverProfile: (vehicleId: number) =>
    get<DriverProfile>(`/api/digital-twin/${vehicleId}/driver-profile`),
  refreshDriverProfile: (vehicleId: number) =>
    post<DriverProfile>(`/api/digital-twin/${vehicleId}/driver-profile/refresh`, {}),

  // ---- Agent Interface ----
  queryAgent: (vehicleId: number, agentType: string, query: string) =>
    post<AgentQueryResponse>(`/api/digital-twin/${vehicleId}/agent/${agentType}`, {
      query,
      agent_type: agentType,
    } as AgentQueryRequest),

  // ---- 365-day Lifecycle Generator ----
  generateLifecycle: (vehicleId: number, force = false) =>
    post<LifecycleGenerationResult>(
      `/api/digital-twin/${vehicleId}/generate-lifecycle${force ? "?force=true" : ""}`,
      {},
    ),
};
