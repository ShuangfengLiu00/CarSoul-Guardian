-- ============================================================================
-- CarSoul Guardian — Agent Evolution Engine (TASK: Evolution Engine)
-- SQLite-compatible database migration — 4 core evolution tables
-- ============================================================================
-- This migration creates the schema for the Agent Evolution Engine, which
-- gives each CarSoul Guardian agent the ability to learn from experience,
-- reflect on outcomes, version its skills, and record its own evolution
-- history. The engine consists of four tables:
--
--   1. experience_memory   — 经验记忆 (cases, solutions, reuse statistics)
--   2. reflection_memory   — 反思记忆 (failure analysis, improvements)
--   3. skill_version        — 技能版本 (versioned capabilities, approval)
--   4. evolution_history    — 进化历史 (milestones, before/after states)
--
-- SQLite notes:
--   * JSON payloads are stored as TEXT (SQLite has no native JSON type;
--     values are serialized JSON strings).
--   * Booleans are stored as INTEGER (0 = false, 1 = true).
--   * Timestamps are stored as TEXT (ISO-8601 strings supplied by the app).
--   * No COMMENT ON syntax is available; column docs live as inline comments.
--
-- Idempotent: each CREATE TABLE and CREATE INDEX is guarded by IF NOT EXISTS.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. experience_memory — 经验记忆表
-- ----------------------------------------------------------------------------
-- Stores solved cases (problem -> solution -> result) so the agent can
-- retrieve and reuse prior experience. Tracks reuse statistics (reuse_count,
-- reuse_success_count) for confidence scoring and pattern mining.
CREATE TABLE IF NOT EXISTS experience_memory (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id               TEXT UNIQUE NOT NULL,
    vehicle_id            TEXT,
    agent_id              TEXT,
    task_type             TEXT NOT NULL,
    problem               TEXT NOT NULL,
    solution              TEXT,
    result                TEXT,
    confidence            REAL DEFAULT 0.0,
    source_data           TEXT,   -- JSON: original request / context payload
    pattern_tags          TEXT,   -- JSON array: e.g. ["battery","cold_start"]
    reuse_count           INTEGER DEFAULT 0,
    reuse_success_count   INTEGER DEFAULT 0,
    created_time          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_experience_task_type ON experience_memory (task_type);
CREATE INDEX IF NOT EXISTS idx_experience_vehicle   ON experience_memory (vehicle_id);
CREATE INDEX IF NOT EXISTS idx_experience_agent     ON experience_memory (agent_id);


-- ----------------------------------------------------------------------------
-- 2. reflection_memory — 反思记忆表
-- ----------------------------------------------------------------------------
-- Records the agent's self-reflection after a task: whether it succeeded,
-- why it failed, and what improvements should follow. Feeds the skill
-- optimization loop and prioritization by improvement_priority.
CREATE TABLE IF NOT EXISTS reflection_memory (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    reflection_id           TEXT UNIQUE NOT NULL,
    task_id                 TEXT,
    agent_id                TEXT NOT NULL,
    task_type               TEXT,
    task_success            INTEGER DEFAULT 0,   -- boolean: 0=false, 1=true
    failure_reason          TEXT,
    improvement             TEXT,                -- JSON array of improvement items
    optimization_strategy   TEXT,
    improvement_priority    TEXT DEFAULT 'low',  -- low | medium | high
    evaluation_id           TEXT,
    trace_id                TEXT,
    created_time            TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reflection_agent    ON reflection_memory (agent_id);
CREATE INDEX IF NOT EXISTS idx_reflection_priority  ON reflection_memory (improvement_priority);


-- ----------------------------------------------------------------------------
-- 3. skill_version — 技能版本表
-- ----------------------------------------------------------------------------
-- Versioned registry of an agent skill. Each version tracks its lineage
-- (parent_version), change log, performance metrics (success_rate, accuracy,
-- performance_score), execution_count, and approval workflow. The
-- (skill_id, version) pair is enforced as UNIQUE.
CREATE TABLE IF NOT EXISTS skill_version (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id              TEXT UNIQUE NOT NULL,
    skill_id                TEXT NOT NULL,
    version                 TEXT NOT NULL,
    parent_version          TEXT,
    change_log              TEXT,
    change_type             TEXT DEFAULT 'initial',
    -- initial | enhance | fix | refactor | rollback
    added_capabilities      TEXT,               -- JSON array of new capability names
    success_rate            REAL DEFAULT 0.0,  -- 0.0-1.0
    accuracy                REAL DEFAULT 0.0,  -- 0.0-1.0
    performance_score       REAL DEFAULT 0.0,  -- 0.0-1.0
    execution_count         INTEGER DEFAULT 0,
    approval_status         TEXT DEFAULT 'pending',
    -- pending | approved | rejected | retired
    approval_notes          TEXT,
    created_time            TEXT NOT NULL,
    deployed_time           TEXT,
    UNIQUE(skill_id, version)
);

CREATE INDEX IF NOT EXISTS idx_skill_version_skill   ON skill_version (skill_id);
CREATE INDEX IF NOT EXISTS idx_skill_version_status  ON skill_version (approval_status);


-- ----------------------------------------------------------------------------
-- 4. evolution_history — 进化历史表
-- ----------------------------------------------------------------------------
-- Append-only log of the agent's evolution milestones: skill evolution,
-- experience discovery, knowledge update, and strategy adjustment. Each
-- event captures before_state / after_state snapshots and impact_metrics
-- for full auditability of how the agent evolved over time.
CREATE TABLE IF NOT EXISTS evolution_history (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id          TEXT UNIQUE NOT NULL,
    agent_id          TEXT,
    milestone_type    TEXT NOT NULL,
    -- skill_evolution | experience_discovery | knowledge_update | strategy_adjustment
    description       TEXT,
    before_state      TEXT,   -- JSON: state snapshot before the event
    after_state       TEXT,   -- JSON: state snapshot after the event
    impact_metrics    TEXT,   -- JSON: e.g. {"success_rate_delta": +0.12}
    timestamp         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evolution_agent  ON evolution_history (agent_id);
CREATE INDEX IF NOT EXISTS idx_evolution_type   ON evolution_history (milestone_type);


-- ============================================================================
-- End of migration — Agent Evolution Engine
-- ============================================================================
-- Verification queries (run manually after applying):
--
--   SELECT name FROM sqlite_master WHERE type='table' AND name IN
--     ('experience_memory','reflection_memory','skill_version','evolution_history');
--
--   SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%';
--
--   SELECT COUNT(*) FROM experience_memory;
--   SELECT * FROM skill_version WHERE approval_status='pending';
--   SELECT * FROM evolution_history ORDER BY timestamp DESC LIMIT 10;
