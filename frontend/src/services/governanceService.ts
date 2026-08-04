/** Governance & Workflow Engine API service.
 *
 * Calls the /api/governance/* endpoints to expose the Agent Governance
 * Layer (registry, permissions, lifecycle), Workflow Engine state
 * (task memories, judge agent), Skill Registry, MCP Registry,
 * Workflow Permissions, Sandbox, Version Manager, and AgentLoop
 * Observation Layer to the frontend.
 */
import { get, post } from "../utils/request";

// ------------------------------------------------------------------
//  Types — Agent Registry
// ------------------------------------------------------------------
export interface AgentMetadata {
  agent_id: string;
  name: string;
  role: string;
  capabilities: string[];
  input_data: string[];
  permissions: string[];
  version: string;
  state: string; // ACTIVE | BUSY | ERROR | UPDATING | OFFLINE
  description: string;
  stats: {
    total_invocations: number;
    success_count: number;
    error_count: number;
    success_rate: number;
    last_invoked: string | null;
  };
  registered_at: string;
}

export interface GovernanceOverview {
  registry: {
    agent_count: number;
    active_count: number;
  };
  fleet_health: {
    total: number;
    active: number;
    busy: number;
    error: number;
    offline: number;
    recent_events: Array<Record<string, unknown>>;
  };
  agents: AgentMetadata[];
}

// ------------------------------------------------------------------
//  Types — Skill Registry
// ------------------------------------------------------------------
export interface SkillMetadata {
  skill_id: string;
  name: string;
  description: string;
  agent_id: string;
  version: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  call_conditions: string;
  category: string;
  registered_at: string;
  stats: {
    total_calls: number;
    success_count: number;
    success_rate: number;
  };
}

// ------------------------------------------------------------------
//  Types — MCP Registry
// ------------------------------------------------------------------
export interface MCPInterface {
  interface_id: string;
  name: string;
  description: string;
  category: string;
  endpoint: string;
  method: string;
  input_params: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  security_level: string;
  registered_at: string;
  stats: {
    total_calls: number;
    success_count: number;
    avg_latency_ms: number;
  };
}

// ------------------------------------------------------------------
//  Types — Workflow Permissions
// ------------------------------------------------------------------
export interface WorkflowPermission {
  workflow_name: string;
  allowed_agents: string[];
  allowed_skills: string[];
  allowed_data: string[];
  denied_actions: string[];
  description: string;
}

// ------------------------------------------------------------------
//  Types — Sandbox
// ------------------------------------------------------------------
export interface SandboxStatus {
  config: {
    max_memory_mb: number;
    max_cpu_percent: number;
    timeout_seconds: number;
    allowed_domains: string[];
    denied_paths: string[];
  };
  active_sessions: number;
  total_executions: number;
  blocked_attempts: number;
}

// ------------------------------------------------------------------
//  Types — Version Manager
// ------------------------------------------------------------------
export interface AgentVersion {
  agent_id: string;
  version: string;
  status: string; // canary | stable | deprecated
  release_date: string;
  canary_percentage: number;
  changes: string;
  metrics: Record<string, number>;
}

// ------------------------------------------------------------------
//  Types — Observation Layer
// ------------------------------------------------------------------
export interface TraceRecord {
  trace_id: string;
  workflow_id: string;
  agent_id: string;
  step: string;
  timestamp: string;
  detail: string;
  duration_ms: number;
  token_usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  data: Record<string, unknown>;
}

export interface TokenStats {
  total_traces: number;
  total_tokens: number;
  avg_tokens_per_trace: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
}

export interface AgentEvaluation {
  agent_id: string;
  accuracy: number;
  response_efficiency: number;
  user_satisfaction: number;
  risk_rate: number;
  total_evaluations: number;
  recent_trend: string;
}

export interface OptimizationAction {
  action_id: string;
  agent_id: string;
  action_type: string;
  description: string;
  priority: string;
  status: string;
  created_at: string;
  expected_improvement: string;
}

export interface EvolutionSummary {
  total_evolutions: number;
  agents_evolved: string[];
  recent_evolution: Record<string, unknown> | null;
  evolution_history: Array<Record<string, unknown>>;
}

// ------------------------------------------------------------------
//  API methods
// ------------------------------------------------------------------
export const governanceService = {
  // --- Agent Registry ---
  async listAgents(): Promise<{ agent_count: number; active_count: number; agents: AgentMetadata[] }> {
    return get("/api/governance/agents");
  },
  async getAgent(agentId: string): Promise<AgentMetadata> {
    return get(`/api/governance/agents/${agentId}`);
  },
  async listPermissions(): Promise<Record<string, unknown>> {
    return get("/api/governance/permissions");
  },
  async fleetHealth(): Promise<Record<string, unknown>> {
    return get("/api/governance/health");
  },
  async lifecycleEvents(limit: number = 50): Promise<{ events: Array<Record<string, unknown>> }> {
    return get(`/api/governance/lifecycle/events?limit=${limit}`);
  },
  async judgeInfo(): Promise<Record<string, unknown>> {
    return get("/api/governance/judge");
  },
  async recentWorkflows(limit: number = 10): Promise<{ workflows: Array<Record<string, unknown>> }> {
    return get(`/api/governance/workflows?limit=${limit}`);
  },
  async overview(): Promise<GovernanceOverview> {
    return get("/api/governance/overview");
  },

  // --- Skill Registry ---
  async listSkills(): Promise<{ skills: SkillMetadata[] }> {
    return get("/api/governance/skills");
  },
  async getSkill(skillId: string): Promise<SkillMetadata> {
    return get(`/api/governance/skills/${skillId}`);
  },
  async skillsByAgent(agentId: string): Promise<{ agent_id: string; skills: SkillMetadata[] }> {
    return get(`/api/governance/skills/agent/${agentId}`);
  },

  // --- MCP Registry ---
  async listMCP(): Promise<{ interfaces: MCPInterface[] }> {
    return get("/api/governance/mcp");
  },
  async getMCP(interfaceId: string): Promise<MCPInterface> {
    return get(`/api/governance/mcp/${interfaceId}`);
  },

  // --- Workflow Permissions ---
  async listWorkflowPermissions(): Promise<{ workflows: WorkflowPermission[] }> {
    return get("/api/governance/workflow-permissions");
  },
  async getWorkflowPermission(workflowName: string): Promise<WorkflowPermission> {
    return get(`/api/governance/workflow-permissions/${workflowName}`);
  },

  // --- Sandbox ---
  async sandboxStatus(): Promise<SandboxStatus> {
    return get("/api/governance/sandbox");
  },

  // --- Version Manager ---
  async listVersions(): Promise<{ versions: AgentVersion[] }> {
    return get("/api/governance/versions");
  },
  async agentVersions(agentId: string): Promise<{ agent_id: string; current: AgentVersion | null; history: AgentVersion[] }> {
    return get(`/api/governance/versions/${agentId}`);
  },
  async promoteCanary(agentId: string, version: string, canaryPercentage: number = 10): Promise<{ success: boolean }> {
    return post("/api/governance/versions/promote-canary", { agent_id: agentId, version, canary_percentage: canaryPercentage });
  },
  async promoteStable(agentId: string, version: string): Promise<{ success: boolean }> {
    return post("/api/governance/versions/promote-stable", { agent_id: agentId, version });
  },

  // --- Observation Layer: Traces ---
  async recentTraces(limit: number = 20): Promise<{ traces: TraceRecord[] | Record<string, TraceRecord[]> }> {
    return get(`/api/governance/observation/traces?limit=${limit}`);
  },
  async getTrace(traceId: string): Promise<TraceRecord | Record<string, unknown>> {
    return get(`/api/governance/observation/traces/${traceId}`);
  },
  async tokenStats(): Promise<TokenStats> {
    return get("/api/governance/observation/token-stats");
  },

  // --- Observation Layer: Evaluation ---
  async evaluationSummary(): Promise<Record<string, unknown>> {
    return get("/api/governance/observation/evaluation");
  },
  async agentEvaluation(agentId: string, limit: number = 50): Promise<{ agent_id: string; evaluations: AgentEvaluation[] }> {
    return get(`/api/governance/observation/evaluation/${agentId}?limit=${limit}`);
  },
  async submitFeedback(workflowId: string, feedback: string, rating: number = 5): Promise<{ success: boolean }> {
    return post("/api/governance/observation/feedback", { workflow_id: workflowId, feedback, rating });
  },

  // --- Observation Layer: Optimization ---
  async pendingOptimizations(): Promise<{ optimizations: OptimizationAction[] }> {
    return get("/api/governance/observation/optimizations");
  },
  async runOptimizationCycle(): Promise<{ generated_actions: number; actions: OptimizationAction[] }> {
    return post("/api/governance/observation/optimizations/run");
  },
  async applyOptimization(actionId: string): Promise<{ success: boolean }> {
    return post("/api/governance/observation/optimizations/apply", { action_id: actionId });
  },

  // --- Observation Layer: Evolution ---
  async evolutionSummary(): Promise<EvolutionSummary> {
    return get("/api/governance/observation/evolution");
  },
  async agentEvolution(agentId: string): Promise<{ agent_id: string; evolution_history: Array<Record<string, unknown>> }> {
    return get(`/api/governance/observation/evolution/${agentId}`);
  },

  // --- Full Overview ---
  async fullOverview(): Promise<Record<string, unknown>> {
    return get("/api/governance/full-overview");
  },
};
