import { get, post, put, del, patch } from "@/utils/request";
import type {
  Vehicle,
  VehicleList,
  VehicleArchive,
  LifecycleEventList,
  LifecycleEvent,
  HealthSnapshotList,
  HealthSnapshot,
  MaintenanceRecordList,
  MaintenanceRecord,
  MaintenanceScheduleList,
  MaintenanceSchedule,
  DrivingBehaviorList,
  DrivingBehavior,
  DrivingBehaviorSummary,
  AlertList,
  Alert,
  OwnershipRecordList,
  OwnershipRecord,
  DigitalTwin,
  SensorData,
  SensorDataList,
  SensorSeries,
  SensorSnapshot,
  Trip,
  TripList,
  TripSummary,
  FaultLog,
  FaultLogList,
  DigitalState,
  VehicleHealthScore,
  VehicleLifeRecord,
  SimulationRequest,
  SimulationResult,
  ServiceOrder,
  ServiceOrderList,
  ServiceOrderCreate,
  ServiceOrderUpdate,
  ServiceOrderFeedback,
} from "./types";

export const vehicleService = {
  // ---- Vehicle CRUD ----
  list: () => get<VehicleList>("/api/vehicle"),
  get: (id: number) => get<Vehicle>(`/api/vehicle/${id}`),
  create: (body: Partial<Vehicle>) => post<Vehicle>("/api/vehicle", body),
  update: (id: number, body: Partial<Vehicle>) => put<Vehicle>(`/api/vehicle/${id}`, body),
  delete: (id: number) => del(`/api/vehicle/${id}`),

  // ---- Archive ----
  getArchive: (id: number) => get<VehicleArchive>(`/api/vehicle/${id}/archive`),

  // ---- Lifecycle ----
  listLifecycle: (id: number, eventType?: string) =>
    get<LifecycleEventList>(`/api/vehicle/${id}/lifecycle${eventType ? `?event_type=${eventType}` : ""}`),
  createLifecycle: (id: number, body: Partial<LifecycleEvent>) =>
    post<LifecycleEvent>(`/api/vehicle/${id}/lifecycle`, body),
  deleteLifecycle: (vehicleId: number, eventId: number) =>
    del(`/api/vehicle/${vehicleId}/lifecycle/${eventId}`),

  // ---- Health ----
  listHealth: (id: number, limit = 20) =>
    get<HealthSnapshotList>(`/api/vehicle/${id}/health?limit=${limit}`),
  getLatestHealth: (id: number) =>
    get<HealthSnapshot | null>(`/api/vehicle/${id}/health/latest`),
  createHealth: (id: number, body: Record<string, unknown>) =>
    post<HealthSnapshot>(`/api/vehicle/${id}/health`, body),

  // ---- Maintenance Records ----
  listMaintenanceRecords: (id: number, limit = 50) =>
    get<MaintenanceRecordList>(`/api/vehicle/${id}/maintenance/records?limit=${limit}`),
  createMaintenanceRecord: (id: number, body: Partial<MaintenanceRecord>) =>
    post<MaintenanceRecord>(`/api/vehicle/${id}/maintenance/records`, body),
  deleteMaintenanceRecord: (vehicleId: number, recordId: number) =>
    del(`/api/vehicle/${vehicleId}/maintenance/records/${recordId}`),

  // ---- Maintenance Schedules ----
  listMaintenanceSchedules: (id: number) =>
    get<MaintenanceScheduleList>(`/api/vehicle/${id}/maintenance/schedules`),
  createMaintenanceSchedule: (id: number, body: Partial<MaintenanceSchedule>) =>
    post<MaintenanceSchedule>(`/api/vehicle/${id}/maintenance/schedules`, body),
  deleteMaintenanceSchedule: (vehicleId: number, scheduleId: number) =>
    del(`/api/vehicle/${vehicleId}/maintenance/schedules/${scheduleId}`),

  // ---- Driving Behavior ----
  listDrivingBehaviors: (id: number, days = 30) =>
    get<DrivingBehaviorList>(`/api/vehicle/${id}/driving-behavior?days=${days}`),
  getDrivingBehaviorSummary: (id: number, days = 30) =>
    get<DrivingBehaviorSummary>(`/api/vehicle/${id}/driving-behavior/summary?days=${days}`),
  createDrivingBehavior: (id: number, body: Partial<DrivingBehavior>) =>
    post<DrivingBehavior>(`/api/vehicle/${id}/driving-behavior`, body),

  // ---- Alerts ----
  listAlerts: (id: number, status?: string, level?: string) =>
    get<AlertList>(`/api/vehicle/${id}/alerts${status ? `?status=${status}` : ""}${level ? `${status ? "&" : "?"}level=${level}` : ""}`),
  createAlert: (id: number, body: Partial<Alert>) =>
    post<Alert>(`/api/vehicle/${id}/alerts`, body),
  updateAlert: (vehicleId: number, alertId: number, body: { status: string }) =>
    patch<Alert>(`/api/vehicle/${vehicleId}/alerts/${alertId}`, body),
  deleteAlert: (vehicleId: number, alertId: number) =>
    del(`/api/vehicle/${vehicleId}/alerts/${alertId}`),

  // ---- Ownership ----
  listOwnership: (id: number) =>
    get<OwnershipRecordList>(`/api/vehicle/${id}/ownership`),
  createOwnership: (id: number, body: Partial<OwnershipRecord>) =>
    post<OwnershipRecord>(`/api/vehicle/${id}/ownership`, body),

  // ---- Service Orders (after-sales closed loop — §3A.1) ----
  listServiceOrders: (id: number, status?: string) =>
    get<ServiceOrderList>(
      `/api/vehicle/${id}/service-orders${status ? `?status=${status}` : ""}`,
    ),
  getServiceOrder: (vehicleId: number, orderId: number) =>
    get<ServiceOrder>(`/api/vehicle/${vehicleId}/service-orders/${orderId}`),
  createServiceOrder: (id: number, body: ServiceOrderCreate) =>
    post<ServiceOrder>(`/api/vehicle/${id}/service-orders`, body),
  advanceServiceOrder: (vehicleId: number, orderId: number, body: ServiceOrderUpdate) =>
    patch<ServiceOrder>(`/api/vehicle/${vehicleId}/service-orders/${orderId}`, body),
  submitServiceFeedback: (vehicleId: number, orderId: number, body: ServiceOrderFeedback) =>
    post<ServiceOrder>(`/api/vehicle/${vehicleId}/service-orders/${orderId}/feedback`, body),
  deleteServiceOrder: (vehicleId: number, orderId: number) =>
    del(`/api/vehicle/${vehicleId}/service-orders/${orderId}`),

  // ---- Digital Twin ----
  getDigitalTwin: (id: number) =>
    get<DigitalTwin | null>(`/api/vehicle/${id}/digital-twin`),
  createDigitalTwin: (id: number, body: Record<string, unknown>) =>
    post<DigitalTwin>(`/api/vehicle/${id}/digital-twin`, body),
  updateDigitalTwin: (id: number, body: Record<string, unknown>) =>
    patch<DigitalTwin>(`/api/vehicle/${id}/digital-twin`, body),
  pushTelemetry: (id: number, telemetry: Record<string, unknown>) =>
    post<DigitalTwin>(`/api/vehicle/${id}/digital-twin/telemetry`, telemetry),

  // ===================================================================
  // TASK007 — Vehicle Digital Life Record APIs
  // ===================================================================

  // ---- Sensor data (IoT telemetry) ----
  listSensors: (id: number, sensorType?: string, limit = 200) =>
    get<SensorDataList>(
      `/api/vehicle/${id}/sensors${sensorType ? `?sensor_type=${sensorType}&limit=${limit}` : `?limit=${limit}`}`,
    ),
  listSensorTypes: (id: number) =>
    get<{ vehicle_id: number; sensor_types: string[] }>(`/api/vehicle/${id}/sensors/types`),
  getSensorSeries: (id: number, sensorType: string, hours = 24) =>
    get<SensorSeries>(`/api/vehicle/${id}/sensors/series?sensor_type=${sensorType}&hours=${hours}`),
  createSensor: (id: number, body: Partial<SensorData>) =>
    post<SensorData>(`/api/vehicle/${id}/sensors`, body),
  createSensorsBatch: (id: number, readings: Partial<SensorData>[]) =>
    post<SensorDataList>(`/api/vehicle/${id}/sensors/batch`, { readings }),

  /**
   * 全车传感器当前快照（6 域 / 58 项信号）。
   * @param params.domain 逗号分隔的域筛选，如 "battery,motor"；缺省返回全部。
   * @param params.include_spec 是否返回量程/阈值/采样率元数据，缺省 true。
   */
  getSensorSnapshot: (id: number, params?: { domain?: string; include_spec?: boolean }) => {
    const search = new URLSearchParams();
    if (params?.domain) search.set("domain", params.domain);
    if (params?.include_spec != null) search.set("include_spec", String(params.include_spec));
    const qs = search.toString();
    return get<SensorSnapshot>(`/api/vehicle/${id}/sensors/snapshot${qs ? `?${qs}` : ""}`);
  },

  // ---- Trips ----
  listTrips: (id: number, limit = 50) =>
    get<TripList>(`/api/vehicle/${id}/trips?limit=${limit}`),
  getTripSummary: (id: number, days = 30) =>
    get<TripSummary>(`/api/vehicle/${id}/trips/summary?days=${days}`),
  createTrip: (id: number, body: Partial<Trip>) =>
    post<Trip>(`/api/vehicle/${id}/trips`, body),
  deleteTrip: (vehicleId: number, tripId: number) =>
    del(`/api/vehicle/${vehicleId}/trips/${tripId}`),

  // ---- Fault logs ----
  listFaults: (id: number, repairStatus?: string, limit = 100) =>
    get<FaultLogList>(
      `/api/vehicle/${id}/faults${repairStatus ? `?repair_status=${repairStatus}&limit=${limit}` : `?limit=${limit}`}`,
    ),
  createFault: (id: number, body: Partial<FaultLog>) =>
    post<FaultLog>(`/api/vehicle/${id}/faults`, body),
  updateFault: (vehicleId: number, faultId: number, body: Partial<FaultLog>) =>
    patch<FaultLog>(`/api/vehicle/${vehicleId}/faults/${faultId}`, body),
  deleteFault: (vehicleId: number, faultId: number) =>
    del(`/api/vehicle/${vehicleId}/faults/${faultId}`),

  // ---- Digital state (real-time) ----
  getDigitalState: (id: number) =>
    get<DigitalState | null>(`/api/vehicle/${id}/digital-state`),
  putDigitalState: (id: number, body: Partial<DigitalState>) =>
    put<DigitalState>(`/api/vehicle/${id}/digital-state`, body),
  patchDigitalState: (id: number, body: Partial<DigitalState>) =>
    patch<DigitalState>(`/api/vehicle/${id}/digital-state`, body),
  deleteDigitalState: (id: number) =>
    del(`/api/vehicle/${id}/digital-state`),

  // ---- Vehicle Digital Life Record (flagship) ----
  getLifeRecord: (id: number) =>
    get<VehicleLifeRecord>(`/api/vehicle/${id}/life`),
  getHealthScore: (id: number) =>
    get<VehicleHealthScore>(`/api/vehicle/${id}/health-score`),

  // ---- Mock data generator / digital-twin simulator ----
  simulate: (id: number, body: SimulationRequest) =>
    post<SimulationResult>(`/api/vehicle/${id}/simulate`, { ...body, vehicle_id: id }),
  simulateQuick: (
    id: number,
    opts?: { sensorPoints?: number; tripCount?: number; faultCount?: number; days?: number },
  ) => {
    const params = new URLSearchParams();
    if (opts?.sensorPoints != null) params.set("sensor_points", String(opts.sensorPoints));
    if (opts?.tripCount != null) params.set("trip_count", String(opts.tripCount));
    if (opts?.faultCount != null) params.set("fault_count", String(opts.faultCount));
    if (opts?.days != null) params.set("days", String(opts.days));
    const qs = params.toString();
    return post<SimulationResult>(
      `/api/vehicle/${id}/simulate/quick${qs ? `?${qs}` : ""}`,
      {},
    );
  },
};
