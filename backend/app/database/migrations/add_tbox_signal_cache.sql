-- T-BOX 信号缓存表（SPEC §6.2 新增表）
--
-- 用途：T-BOX 适配层 cached 层的持久化存储，跨进程/重启保留最近一次读数。
-- MVP 阶段适配器使用进程级内存缓存；此表为 Phase 2 DB-backed cache 预留，
-- 届时 _read_cached/_generate_mock 可经 conn 写入/读出此表。
--
-- 字段说明：
--   data_source   取值 live/cached/mock/unavailable（C-05 透传）
--   confidence    live=1.0 / cached=0.7 / mock=0.3 / unavailable=0.0
--   quality_flags JSON 数组字符串，如 '["simulated","stale"]'
--   expires_at    ISO8601 过期时间，按 5 频率层 TTL 计算
CREATE TABLE IF NOT EXISTS tbox_signal_cache (
    signal_id      TEXT    NOT NULL,
    vehicle_id     TEXT    NOT NULL,
    value          REAL,
    unit           TEXT,
    timestamp      TEXT    NOT NULL,
    data_source    TEXT    NOT NULL DEFAULT 'mock',
    confidence     REAL    NOT NULL DEFAULT 0.3,
    quality_flags  TEXT,
    expires_at     TEXT    NOT NULL,
    PRIMARY KEY (signal_id, vehicle_id)
);

-- 按车辆 + 过期时间检索，支撑 cached 层批量失效与巡检清理。
CREATE INDEX IF NOT EXISTS idx_tbox_cache_vehicle
    ON tbox_signal_cache (vehicle_id, expires_at);
