/**
 * Timeline Demo Types — mirrors backend `app/schemas/timeline.py`.
 */

export interface TelemetrySnapshot {
  day: number;
  mileage: number;
  soh: number;
  battery_temp: number;
  charging_speed_ratio: number;
  charge_cycles: number;
  fast_charge_ratio: number;
}

export interface MemoryEntry {
  id: string;
  event_type: string;
  summary: string;
  impact_target: string | null;
  impact_delta: number;
  occurred_at: string;
  source: string;
}

export interface TimelineEvent {
  day: number;
  date: string;
  title: string;
  description: string;
  event_type: string;
  mileage: number | null;
}

export interface AgentFinding {
  agent_name: string;
  skill_name: string;
  severity: string;
  finding: string;
  recommendation: string;
  confidence: number;
}

export interface AgentCollaboration {
  triggered: boolean;
  trigger_reason: string | null;
  guardian_summary: string | null;
  findings: AgentFinding[];
}

export interface TimelinePhase {
  year: number;
  label: string;
  summary: string;
  color: string;
  telemetry: TelemetrySnapshot;
  events: TimelineEvent[];
  memories: MemoryEntry[];
  agent_collaboration: AgentCollaboration | null;
}

export interface TraceableItem {
  label: string;
  value: string;
  source_type: string;
  source_id: string;
  source_description: string;
}

export interface UsedCarValuation {
  current: number;
  projected: number;
  delta: number;
}

export interface HealthReport {
  health_score: number;
  health_grade: string;
  battery_degradation_12m: number;
  charging_strategy: string;
  used_car_valuation: UsedCarValuation;
  traceable_items: TraceableItem[];
}

export interface VehicleInfo {
  vin: string;
  name: string;
  profile: string;
  brand: string;
  model: string;
}

export interface LifeStoryResponse {
  vehicle: VehicleInfo;
  phases: TimelinePhase[];
  report: HealthReport;
  demo_mode: boolean;
}
