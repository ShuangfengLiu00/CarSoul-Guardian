-- Orchestrator 调度记录表（SPEC §6.2 新增表）
--
-- agent_dispatch_log: Orchestrator 每次调度的审计记录（C-03 全链路可追溯）
-- agent_artifact:     Agent 间共享的上下文产物（串行链中间结果）
--
-- 字段说明：
--   mode           single / serial / parallel（SPEC §4.4 调度模式）
--   status         pending / ok / degraded / refused / clarify / failed
--   target_agents  JSON 数组字符串，如 '["usage_assistant","after_sales"]'
--   subtask_count  子任务数（serial=链长，parallel=链数）
--   audit_hash     哈希链校验值（与 ActionStore 哈希链对齐）
--   value          JSON 字符串，Agent 产出的结构化数据

CREATE TABLE IF NOT EXISTS agent_dispatch_log (
    dispatch_id    TEXT     NOT NULL PRIMARY KEY,
    user_input     TEXT     NOT NULL,
    target_agents  TEXT     NOT NULL DEFAULT '[]',
    subtask_count  INTEGER  NOT NULL DEFAULT 1,
    mode           TEXT     NOT NULL DEFAULT 'single',
    status         TEXT     NOT NULL DEFAULT 'pending',
    audit_hash     TEXT,
    created_at     TEXT     NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_artifact (
    artifact_id    TEXT     NOT NULL PRIMARY KEY,
    dispatch_id    TEXT     NOT NULL,
    agent_name     TEXT     NOT NULL,
    key            TEXT     NOT NULL,
    value          TEXT,
    created_at     TEXT     NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (dispatch_id) REFERENCES agent_dispatch_log(dispatch_id)
);

-- 按调度 ID 检索产物（串行链中间结果回溯）
CREATE INDEX IF NOT EXISTS idx_artifact_dispatch
    ON agent_artifact (dispatch_id);
