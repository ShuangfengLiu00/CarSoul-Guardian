/**
 * PLACEHOLDER — evolutionService
 * ------------------------------------------------------------------
 * EvolutionEngine.tsx depends on this module, but the real backing
 * service (a world-model "evolution / skill-mutation" backend) is not
 * implemented yet. This stub keeps the app buildable and lets the page
 * render empty/safe states.
 *
 * The return shapes below mirror what EvolutionEngine.tsx renders.
 * All methods resolve to empty/safe defaults (no real data), which is
 * consistent with the demo badge on this page.
 *
 * TODO: wire these methods to the CarSoul World Model (carModel) once an
 * evolution / timeline / skill-proposal endpoint exists.
 */

// ---- Dashboard sub-shapes -------------------------------------------------
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
}

// ---- Experience -----------------------------------------------------------
export interface ExperienceCase {
  id: string;
  title: string;
  summary: string;
  tags: string[];
  createdAt: string;
}

// ---- Experience patterns --------------------------------------------------
export interface ExperiencePattern {
  id: string;
  name: string;
  confidence: number;
  description: string;
  pattern_name?: string;
  occurrence_count?: number;
  // success_rate 在页面中按必填参与数值比较（p.success_rate > 0.7），故置为非可选。
  success_rate: number;
  common_solution?: string;
}

// ---- Reflection reports ---------------------------------------------------
export interface ReflectionAnalysis {
  strengths?: string[];
  weaknesses?: string[];
  improvements?: string[];
  new_knowledge?: string;
}

export interface ReflectionTaskLayer {
  task_success?: boolean;
}

export interface ReflectionReport {
  id: string;
  content: string;
  createdAt: string;
  reflection_id?: string;
  task_type?: string;
  agent_id?: string;
  task_layer?: ReflectionTaskLayer;
  improvement_priority?: string;
  timestamp?: string;
  analysis?: ReflectionAnalysis;
  reasoning_layer?: {
    reasoning_errors?: string[];
    missing_data?: string[];
  };
}

// ---- Skill mutation proposals ---------------------------------------------
export type ProposalStatus = "pending" | "approved" | "rejected" | "proposed";

export interface SkillMutationProposal {
  id: string;
  title: string;
  rationale: string;
  status: ProposalStatus;
  impact: string;
  // proposal_id 在页面中按必填直接传给 handleApprove(record.proposal_id)，故置为非可选。
  proposal_id: string;
  changes?: string[];
  added_capabilities?: string[];
  test_result?: Record<string, unknown>;
  sandbox_result?: Record<string, unknown>;
}

// ---- Timeline -------------------------------------------------------------
export type ImpactLevel = "high" | "medium" | "low" | (string & {});

export interface EvolutionTimelineEntry {
  id: string;
  at: string;
  event: string;
  detail: string;
  event_type: string;
  timestamp?: string;
  agent_id?: string;
  impact_level?: ImpactLevel;
  title?: string;
  description?: string;
}

export interface CycleResult {
  cycleId: string;
  status: string;
  changes: number;
}

const EMPTY = <T,>(v: T): Promise<T> => Promise.resolve(v);

export const evolutionService = {
  experienceCases: (): Promise<{ cases: ExperienceCase[] }> =>
    EMPTY<{ cases: ExperienceCase[] }>({ cases: [] }),
  experiencePatterns: (): Promise<{ patterns: ExperiencePattern[] }> =>
    EMPTY<{ patterns: ExperiencePattern[] }>({ patterns: [] }),
  searchExperience: (_query: string): Promise<{ results: ExperienceCase[] }> =>
    EMPTY<{ results: ExperienceCase[] }>({ results: [] }),
  recentReflections: (_n: number): Promise<{ reflections: ReflectionReport[] }> =>
    EMPTY<{ reflections: ReflectionReport[] }>({ reflections: [] }),
  skillProposals: (_n: number): Promise<{ proposals: SkillMutationProposal[] }> =>
    EMPTY<{ proposals: SkillMutationProposal[] }>({ proposals: [] }),
  approveProposal: (_id: string) => EMPTY<{ ok: boolean }>({ ok: true }),
  timeline: (_n: number): Promise<{ entries: EvolutionTimelineEntry[] }> =>
    EMPTY<{ entries: EvolutionTimelineEntry[] }>({ entries: [] }),
  dashboard: (): Promise<EvolutionDashboard> =>
    EMPTY<EvolutionDashboard>({
      experience: {},
      reflection: {},
      skill_evolution: {},
      evaluation: {},
      evolution_memory: {},
      engine_enabled: false,
      total_cycles: 0,
      last_cycle: null,
    }),
  runCycle: (): Promise<CycleResult> =>
    EMPTY<CycleResult>({ cycleId: "stub", status: "noop", changes: 0 }),
  seedDemo: () => EMPTY<{ seeded: number }>({ seeded: 0 }),
};

export default evolutionService;
