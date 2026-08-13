-- ============================================================================
-- CarSoul Guardian — Orchestrator Dispatch Tables (TASK: T2 Orchestrator)
-- SQLite-compatible database migration — 2 tables for dispatch logging
-- ============================================================================
-- This migration creates the schema for the Orchestrator 总控调度器 audit trail:
--
--   1. agent_dispatch_log  — 调度记录（每次 dispatch 的意图/路由/状态/耗时）
--   2. agent_artifact      — Agent 产物（每个参与 Agent 的结果/置信度/数据源）
--
-- SQLite notes:
--   * JSON payloads are stored as TEXT (serialized JSON strings).
--   * Booleans are stored as INTEGER (0 = false, 1 = true).
--   * Timestamps are stored as TEXT (ISO-8601 strings supplied by the app).
--   * Idempotent: each CREATE TABLE / CREATE INDEX is guarded by IF NOT EXISTS.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. agent_dispatch_log — 调度记录表
-- ----------------------------------------------------------------------------
-- One row per Orchestrator.dispatch() call. Records the user message, matched
-- intent, agents involved, execution mode (single/serial/parallel), final
-- status and total duration for observability and debugging.
CREATE TABLE IF NOT EXISTS agent_dispatch_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    dispatch_id       TEXT    NOT NULL UNIQUE,
    user_id           TEXT    NOT NULL DEFAULT 'anonymous',
    user_message      TEXT    NOT NULL,
    intent_match      TEXT    NOT NULL DEFAULT '',   -- matched agent_name or ''
    agents_involved   TEXT    NOT NULL DEFAULT '[]', -- JSON array of agent names
    execution_mode    TEXT    NOT NULL DEFAULT 'single', -- single|serial|parallel|none
    status            TEXT    NOT NULL DEFAULT 'ok', -- ok|degraded|refused|clarify|failed
    duration_ms       INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_dispatch_log_user
    ON agent_dispatch_log(user_id);
CREATE INDEX IF NOT EXISTS idx_dispatch_log_created
    ON agent_dispatch_log(created_at);


-- ----------------------------------------------------------------------------
-- 2. agent_artifact — Agent 产物表
-- ----------------------------------------------------------------------------
-- One row per participating Agent in a dispatch. Stores the AgentResult payload
-- (JSON), confidence score and data source (real/simulated) for traceability
-- and downstream aggregation. dispatch_id references agent_dispatch_log.
CREATE TABLE IF NOT EXISTS agent_artifact (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    dispatch_id       TEXT    NOT NULL,
    agent_name        TEXT    NOT NULL,
    result_json       TEXT    NOT NULL DEFAULT '{}', -- serialized AgentResult
    confidence        REAL,                          -- NULL when not applicable
    data_source       TEXT    NOT NULL DEFAULT '',   -- real | simulated | ''
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    FOREIGN KEY (dispatch_id) REFERENCES agent_dispatch_log(dispatch_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_artifact_dispatch
    ON agent_artifact(dispatch_id);
CREATE INDEX IF NOT EXISTS idx_artifact_agent
    ON agent_artifact(agent_name);
