/**
 * Evolution Engine API service.
 *
 * Calls the /api/governance/evolution/* endpoints on the Guardian backend
 * (:8001) to expose the Agent Evolution Engine — experience mining,
 * reflection engine, skill evolution, and evolution timeline — to the
 * frontend Dashboard.
 *
 * All endpoints are backed by carsoul_agent.observation.* (2858 lines of
 * real engine logic).  Data lives in process memory; restart clears it.
 */
import { get, post } from "../utils/request";

// ------------------------------------------------------------------
//  Types — Dashboard
// ------------------------------------------------------------------
export interface ExperienceStats {
  total_cases?: number;
  total_patterns?: number;
  avg_confidence?: number;
}

export interface ReflectionStats {
  success_rate?: number;
  total_reflections?: number;
  high_priority_count?: number;
  agents_reflected?: number;
}

export interface SkillEvolutionStats {
  total_versions?: number;
  tracked_skills?: number;
  pending_proposals?: number;
  deployed_versions?: number;
}

export interface EvaluationStats {
  total_evaluations?: number;
  feedback_count?: number;
}

export interface EvolutionMemoryStats {
  total_milestones?: number;
  unique_agents?: number;
  milestone_type_breakdown?: Record<string, number>;
}

export interface LastCycle {
  cycle_id?: string;
  started_at?: string;
  completed_at?: string;
  experiences_mined?: number;
  patterns_discovered?: number;
  improvements_generated?: number;
  skills_evolved?: string[];
  success?: boolean;
  summary?: string;
}

export interface EvolutionDashboard {
  experience: ExperienceStats;
  reflection: ReflectionStats;
  skill_evolution: SkillEvolutionStats;
  evaluation: EvaluationStats;
  evolution_memory: EvolutionMemoryStats;
  engine_enabled: boolean;
  total_cycles: number;
  last_cycle: LastCycle | null;
  /** 后端 get_dashboard() 多返回 optimization 摘要 */
  optimization?: Record<string, unknown>;
}

// ------------------------------------------------------------------
//  Types — Experience (aligned with experience_miner.to_dict())
// ------------------------------------------------------------------
export interface ExperienceCase {
  case_id: string;
  vehicle_id?: string;
  agent_id?: string;
  task_type: string;
  problem: string;
  solution?: string;
  result?: string;
  confidence: number;
  reuse_count?: number;
  reuse_success_count?: number;
  created_time: string;
  pattern_tags?: string[];
}

// ------------------------------------------------------------------
//  Types — Experience Patterns
// ------------------------------------------------------------------
export interface ExperiencePattern {
  pattern_id?: string;
  pattern_name: string;
  description: string;
  confidence: number;
  success_rate: number;
  occurrence_count?: number;
  common_solution?: string;
  task_types?: string[];
}

// ------------------------------------------------------------------
//  Types — Reflection Reports (aligned with reflection_engine.to_dict())
// ------------------------------------------------------------------
export interface ReflectionAnalysis {
  strengths?: string[];
  weaknesses?: string[];
  improvements?: string[];
  new_knowledge?: string;
}

export interface ReflectionTaskLayer {
  task_success?: boolean;
  user_problem_solved?: boolean;
}

export interface ReflectionReasoningLayer {
  correct_agent_called?: boolean;
  missing_data?: string[];
  reasoning_errors?: string[];
}

export interface ReflectionResultLayer {
  prediction_accurate?: boolean;
  user_satisfied?: boolean;
}

export interface ReflectionReport {
  reflection_id: string;
  agent_id?: string;
  task_type?: string;
  timestamp?: string;
  task_layer?: ReflectionTaskLayer;
  reasoning_layer?: ReflectionReasoningLayer;
  result_layer?: ReflectionResultLayer;
  analysis?: ReflectionAnalysis;
  improvement_priority?: string;
  /** Legacy fields kept for render compat */
  id?: string;
  content?: string;
  createdAt?: string;
}

// ------------------------------------------------------------------
//  Types — Skill Mutation Proposals (aligned with skill_evolution_engine)
// ------------------------------------------------------------------
export type ProposalStatus = "pending" | "approved" | "rejected" | "proposed" | "testing" | "sandbox" | "deployed";

export interface SkillMutationProposal {
  proposal_id: string;
  skill_id: string;
  mutation_type: string;
  current_version: string;
  proposed_version: string;
  mutation_reason?: string;
  approval_score: number;
  status: ProposalStatus | string;
  changes?: string[];
  added_capabilities?: string[];
  test_result?: Record<string, unknown>;
  sandbox_result?: Record<string, unknown>;
  /** Legacy fields kept for render compat */
  id?: string;
  title?: string;
  rationale?: string;
  impact?: string;
}

// ------------------------------------------------------------------
//  Types — Timeline (backend returns {timeline: [...]})
// ------------------------------------------------------------------
export type ImpactLevel = "high" | "medium" | "low" | (string & {});

export interface EvolutionTimelineEntry {
  milestone_id?: string;
  milestone_type?: string;
  description: string;
  timestamp: string;
  agent_id?: string;
  impact_metrics?: Record<string, unknown>;
  /** Render-compat aliases */
  id?: string;
  at?: string;
  event?: string;
  detail?: string;
  event_type: string;  // always populated by timeline() mapper
  title: string;       // always populated by timeline() mapper
  impact_level?: ImpactLevel;
}

// ------------------------------------------------------------------
//  Types — Cycle Result
// ------------------------------------------------------------------
export interface CycleResult {
  cycle_id: string;
  status: string;
  success: boolean;
  experiences_mined: number;
  patterns_discovered: number;
  reflections_generated: number;
  skills_evolved: number;
  improvements_generated: number;
  summary: string;
  started_at?: string;
  completed_at?: string;
  /** Legacy alias */
  changes?: number;
  /** Legacy alias */
  cycleId?: string;
}

// ------------------------------------------------------------------
//  API methods
// ------------------------------------------------------------------
const EV = "/api/governance/evolution";

export const evolutionService = {
  // --- Dashboard ---
  async dashboard(): Promise<EvolutionDashboard> {
    return get<EvolutionDashboard>(`${EV}/dashboard`);
  },

  // --- Cycle control ---
  async runCycle(): Promise<CycleResult> {
    return post<CycleResult>(`${EV}/run-cycle`);
  },

  async seedDemo(): Promise<{ seeded: number; message?: string }> {
    return post<{ seeded: number; message?: string }>(`${EV}/seed-demo`);
  },

  // --- Experience ---
  async experienceCases(limit: number = 100): Promise<{ cases: ExperienceCase[] }> {
    return get<{ cases: ExperienceCase[] }>(`${EV}/experience/cases?limit=${limit}`);
  },

  async experiencePatterns(): Promise<{ patterns: ExperiencePattern[] }> {
    return get<{ patterns: ExperiencePattern[] }>(`${EV}/experience/patterns`);
  },

  /**
   * Search similar experiences.
   * Backend requires `task_type` as a query param; when the frontend
   * passes a free-text query we send it as both task_type and problem
   * so the backend's retrieve_similar() can do its best match.
   */
  async searchExperience(query: string): Promise<{ results: ExperienceCase[]; task_type: string; problem: string }> {
    return get(`${EV}/experience/search?task_type=${encodeURIComponent(query)}&problem=${encodeURIComponent(query)}&limit=10`);
  },

  // --- Reflection ---
  async recentReflections(limit: number = 20): Promise<{ reflections: ReflectionReport[] }> {
    return get<{ reflections: ReflectionReport[] }>(`${EV}/reflection/recent?limit=${limit}`);
  },

  // --- Skill Evolution ---
  async skillProposals(limit: number = 50): Promise<{ proposals: SkillMutationProposal[] }> {
    return get<{ proposals: SkillMutationProposal[] }>(`${EV}/skill/proposals?limit=${limit}`);
  },

  async approveProposal(proposalId: string): Promise<{ approved: boolean; proposal_id: string; status: string }> {
    return post(`${EV}/skill/approve`, { proposal_id: proposalId });
  },

  // --- Timeline ---
  /**
   * Backend returns `{timeline: EvolutionMilestone[]}`.
   * We map it to `{entries: [...]}` so the existing TimelineTab render
   * keeps working without changes.
   */
  async timeline(limit: number = 50): Promise<{ entries: EvolutionTimelineEntry[] }> {
    const raw = await get<{ timeline: EvolutionTimelineEntry[] }>(`${EV}/memory/timeline?limit=${limit}`);
    // Map backend field names to what the frontend renderer expects
    const entries: EvolutionTimelineEntry[] = (raw.timeline || []).map((m) => ({
      ...m,
      id: m.milestone_id ?? m.id ?? "",
      event_type: m.milestone_type ?? m.event_type ?? "milestone",
      title: m.title ?? m.milestone_type ?? "事件",
      description: m.description ?? m.detail ?? "",
      at: m.timestamp ?? m.at ?? "",
      timestamp: m.timestamp,
      impact_level: (m.impact_metrics?.score as ImpactLevel) ?? m.impact_level ?? "medium",
    }));
    return { entries };
  },
};

export default evolutionService;
