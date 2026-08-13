-- 003_external_service_audit.sql
-- 外部服务调用审计留痕表（T5: ExternalServiceAdapter 落账）
-- 每次 third_party_api 工具调用（live/mock/unavailable）写一条记录。
-- C-15: 审计事件必须包含 data_source 和 confidence 字段。

CREATE TABLE IF NOT EXISTS external_service_audit (
    audit_id      TEXT PRIMARY KEY,
    service_name  TEXT NOT NULL,
    method        TEXT NOT NULL,
    params        TEXT,           -- JSON，脱敏后存储
    result        TEXT,           -- JSON，脱敏后存储
    data_source   TEXT NOT NULL,  -- live / mock / unavailable
    confidence    REAL NOT NULL,
    latency_ms    INTEGER,
    degrade_code  TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_esa_service_method
    ON external_service_audit(service_name, method);
CREATE INDEX IF NOT EXISTS idx_esa_created_at
    ON external_service_audit(created_at);
