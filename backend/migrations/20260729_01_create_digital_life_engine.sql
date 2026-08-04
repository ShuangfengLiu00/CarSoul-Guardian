-- ============================================================================
-- CarSoul Guardian — Vehicle Digital Life Engine (TASK007-V2)
-- Digital Twin Database — 8 core digital-life tables
-- ============================================================================
-- This migration adds the "digital life" narrative layer on top of the
-- existing vehicle digital-life archive (TASK007). Each vehicle now has:
--
--   1. vehicle_identity        — 数字身份 (CSG-YYYY-NNNNN soul ID)
--   2. vehicle_life_state      — 生命状态 (life stage, health dimensions)
--   3. vehicle_health_metrics   — 细分健康 (component-level health, wear, risk)
--   4. vehicle_sensor_stream    — 传感器时间序列 (high-frequency telemetry)
--   5. vehicle_life_event       — 生命周期事件 ⭐ (with importance scoring)
--   6. vehicle_memory           — 车辆记忆系统 ⭐ (AI context memory)
--   7. driver_profile           — 驾驶人格模型 (driver style, scores)
--   8. vehicle_prediction       — AI预测结果 (target component, confidence)
--
-- All tables reference the existing `vehicles` table as the root entity.
-- Idempotent: each CREATE TABLE is guarded by IF NOT EXISTS.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. vehicle_identity — 车辆数字身份 (出生证明)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicle_identity (
    id              BIGSERIAL    PRIMARY KEY,
    vehicle_id      BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    vehicle_uuid    VARCHAR(50)  UNIQUE NOT NULL,   -- CSG-2026-00001

    vin             VARCHAR(50),
    brand           VARCHAR(50),
    model           VARCHAR(100),
    production_year INT,
    energy_type     VARCHAR(30),                    -- electric | gasoline | hybrid | ...
    vehicle_class   VARCHAR(50),                    -- SUV | sedan | hatchback | ...

    owner_id        BIGINT,
    birth_time      TIMESTAMP,                      -- 车辆"出生"时间
    nickname        VARCHAR(64),

    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_vehicle_identity_vehicle UNIQUE (vehicle_id)
);

CREATE INDEX IF NOT EXISTS ix_vehicle_identity_uuid   ON vehicle_identity (vehicle_uuid);
CREATE INDEX IF NOT EXISTS ix_vehicle_identity_owner  ON vehicle_identity (owner_id);

COMMENT ON TABLE  vehicle_identity IS '车辆数字身份 — 车辆的出生证明和灵魂ID.';
COMMENT ON COLUMN vehicle_identity.vehicle_uuid IS '灵魂ID格式: CSG-YYYY-NNNNN';
COMMENT ON COLUMN vehicle_identity.energy_type IS 'electric | gasoline | diesel | hybrid | plug_in_hybrid';
COMMENT ON COLUMN vehicle_identity.birth_time IS '车辆"出生"时间 — 购买或首次激活时刻';


-- ----------------------------------------------------------------------------
-- 2. vehicle_life_state — 车辆生命状态 (当前生命体征)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicle_life_state (
    id                  BIGSERIAL    PRIMARY KEY,
    vehicle_id          BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    health_score        FLOAT,                         -- 0-100 综合健康
    life_stage          VARCHAR(30)  NOT NULL DEFAULT 'NEW',
    -- NEW | GROWTH | MATURE | AGING | RETIRE

    mileage             BIGINT       NOT NULL DEFAULT 0,
    vehicle_age_days    INT          NOT NULL DEFAULT 0,

    energy_health       FLOAT,                         -- 能源系统健康 0-100
    mechanical_health  FLOAT,                         -- 机械系统健康 0-100
    software_health     FLOAT,                         -- 软件系统健康 0-100

    soul_score          FLOAT,                         -- VSS 车辆灵魂指数 0-100

    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_vehicle_life_state_vehicle UNIQUE (vehicle_id)
);

CREATE INDEX IF NOT EXISTS ix_vehicle_life_state_vehicle   ON vehicle_life_state (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_life_state_stage     ON vehicle_life_state (life_stage);

COMMENT ON TABLE  vehicle_life_state IS '车辆当前生命状态 — 生命体征快照.';
COMMENT ON COLUMN vehicle_life_state.life_stage IS 'NEW | GROWTH | MATURE | AGING | RETIRE';
COMMENT ON COLUMN vehicle_life_state.soul_score IS 'Vehicle Soul Score (VSS) — 灵魂指数';


-- ----------------------------------------------------------------------------
-- 3. vehicle_health_metrics — 车辆健康指标 (细分健康)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicle_health_metrics (
    id              BIGSERIAL    PRIMARY KEY,
    vehicle_id      BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    component       VARCHAR(50)  NOT NULL,   -- battery | motor | brake | tire | body | electronics | cooling
    health_score    FLOAT,                    -- 0-100
    temperature     FLOAT,                    -- ℃
    wear_level      FLOAT,                    -- 0-100 (0=全新, 100=完全磨损)
    risk_level      VARCHAR(20)  NOT NULL DEFAULT 'low',  -- low | medium | high | critical

    record_time     TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_health_metrics_vehicle   ON vehicle_health_metrics (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_health_metrics_component ON vehicle_health_metrics (component);
CREATE INDEX IF NOT EXISTS ix_vehicle_health_metrics_risk      ON vehicle_health_metrics (risk_level);
CREATE INDEX IF NOT EXISTS ix_vehicle_health_metrics_time      ON vehicle_health_metrics (record_time);

COMMENT ON TABLE  vehicle_health_metrics IS '车辆健康指标 — 组件级细分健康数据.';
COMMENT ON COLUMN vehicle_health_metrics.component IS 'battery | motor | brake | tire | body | electronics | cooling';
COMMENT ON COLUMN vehicle_health_metrics.risk_level IS 'low | medium | high | critical';
COMMENT ON COLUMN vehicle_health_metrics.wear_level IS '0=全新, 100=完全磨损';


-- ----------------------------------------------------------------------------
-- 4. vehicle_sensor_stream — 车辆传感器时间序列
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicle_sensor_stream (
    id              BIGSERIAL    PRIMARY KEY,
    vehicle_id      BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    sensor_name     VARCHAR(50)  NOT NULL,   -- battery_temperature | motor_speed | brake_pressure | ...
    value           FLOAT        NOT NULL,
    unit            VARCHAR(20),             -- ℃ | rpm | % | bar | V | kW
    meta            JSONB,                   -- optional metadata

    timestamp       TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_sensor_stream_vehicle ON vehicle_sensor_stream (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_sensor_stream_name    ON vehicle_sensor_stream (sensor_name);
CREATE INDEX IF NOT EXISTS ix_vehicle_sensor_stream_time   ON vehicle_sensor_stream (timestamp);

CREATE INDEX IF NOT EXISTS ix_vehicle_sensor_stream_vname_time
    ON vehicle_sensor_stream (vehicle_id, sensor_name, timestamp DESC);

COMMENT ON TABLE vehicle_sensor_stream IS '车辆传感器时间序列 — 高频遥测数据流.';


-- ----------------------------------------------------------------------------
-- 5. vehicle_life_event — 车辆生命事件 ⭐核心
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicle_life_event (
    id              BIGSERIAL    PRIMARY KEY,
    vehicle_id      BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    event_type      VARCHAR(50)  NOT NULL,
    -- PURCHASE | FIRST_DRIVE | TRAVEL | MAINTENANCE | ACCIDENT | WARNING | RECOVERY | UPGRADE | CUSTOM

    title           VARCHAR(200) NOT NULL,
    description     TEXT,

    importance      INT          NOT NULL DEFAULT 5,  -- 1-10 (10=最重要)
    mileage         BIGINT,
    location        VARCHAR(256),
    cost            DOUBLE PRECISION,
    extra_data      JSONB,

    event_time      TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_life_event_vehicle ON vehicle_life_event (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_life_event_type   ON vehicle_life_event (event_type);
CREATE INDEX IF NOT EXISTS ix_vehicle_life_event_time   ON vehicle_life_event (event_time);
CREATE INDEX IF NOT EXISTS ix_vehicle_life_event_imp    ON vehicle_life_event (importance);

COMMENT ON TABLE  vehicle_life_event IS '车辆生命事件 — 区别普通车机的核心叙事表.';
COMMENT ON COLUMN vehicle_life_event.event_type IS 'PURCHASE | FIRST_DRIVE | TRAVEL | MAINTENANCE | ACCIDENT | WARNING | RECOVERY | UPGRADE | CUSTOM';
COMMENT ON COLUMN vehicle_life_event.importance IS '1-10, 10=最重要';


-- ----------------------------------------------------------------------------
-- 6. vehicle_memory — 车辆记忆系统 ⭐ (AI上下文记忆)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicle_memory (
    id              BIGSERIAL    PRIMARY KEY,
    vehicle_id      BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    memory_type     VARCHAR(50)  NOT NULL,
    -- habit | event | preference | warning | recovery | emotion | context

    content         TEXT         NOT NULL,
    emotion_score   FLOAT,                      -- -1.0 to 1.0 (negative to positive)
    importance      INT          NOT NULL DEFAULT 5,  -- 1-10

    source          VARCHAR(50)  NOT NULL DEFAULT 'system',  -- system | agent | user | sensor
    meta_data       JSONB,

    created_time    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_memory_vehicle ON vehicle_memory (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_memory_type   ON vehicle_memory (memory_type);
CREATE INDEX IF NOT EXISTS ix_vehicle_memory_time   ON vehicle_memory (created_time);

COMMENT ON TABLE  vehicle_memory IS '车辆记忆系统 — 让AI拥有上下文.';
COMMENT ON COLUMN vehicle_memory.memory_type IS 'habit | event | preference | warning | recovery | emotion | context';
COMMENT ON COLUMN vehicle_memory.emotion_score IS '-1.0 (消极) to 1.0 (积极)';
COMMENT ON COLUMN vehicle_memory.source IS 'system | agent | user | sensor';


-- ----------------------------------------------------------------------------
-- 7. driver_profile — 驾驶人格模型
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS driver_profile (
    id                  BIGSERIAL    PRIMARY KEY,
    vehicle_id          BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    driver_style        VARCHAR(50)  NOT NULL DEFAULT 'balanced',
    -- conservative | balanced | aggressive | eco | sporty

    aggressive_score    FLOAT,       -- 0-100 (higher = more aggressive)
    comfort_score       FLOAT,       -- 0-100
    eco_score           FLOAT,       -- 0-100

    total_trips         INT          NOT NULL DEFAULT 0,
    total_distance      FLOAT        NOT NULL DEFAULT 0,   -- km
    total_duration      INT          NOT NULL DEFAULT 0,    -- minutes
    total_harsh_events INT          NOT NULL DEFAULT 0,

    preferred_speed_range  VARCHAR(30),   -- "30-60" km/h
    preferred_driving_time VARCHAR(30),   -- "morning" | "evening" | "night" | "mixed"
    preferred_road_type    VARCHAR(30),   -- "urban" | "highway" | "mixed"

    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_driver_profile_vehicle UNIQUE (vehicle_id)
);

CREATE INDEX IF NOT EXISTS ix_driver_profile_vehicle ON driver_profile (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_driver_profile_style  ON driver_profile (driver_style);

COMMENT ON TABLE  driver_profile IS '驾驶人格模型 — 车辆对车主驾驶风格的认知.';
COMMENT ON COLUMN driver_profile.driver_style IS 'conservative | balanced | aggressive | eco | sporty';


-- ----------------------------------------------------------------------------
-- 8. vehicle_prediction — AI预测结果表
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicle_prediction (
    id                  BIGSERIAL    PRIMARY KEY,
    vehicle_id          BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    target_component    VARCHAR(50)  NOT NULL,   -- battery | brake | tire | motor | ...
    prediction          TEXT         NOT NULL,   -- 人类可读的预测描述
    risk_level          VARCHAR(20)  NOT NULL DEFAULT 'low',  -- low | medium | high | critical
    confidence          FLOAT,                   -- 0.0-1.0

    predicted_value     FLOAT,                   -- 预测值 (如剩余km)
    predicted_unit      VARCHAR(20),             -- km | days | cycles
    predicted_time      TIMESTAMP,              -- 预计发生时间

    root_cause          TEXT,
    suggestion          TEXT,

    status              VARCHAR(20)  NOT NULL DEFAULT 'active',  -- active | confirmed | false_alarm | expired
    actual_outcome      VARCHAR(20),            -- confirmed | false_alarm | no_event

    prediction_time     TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_prediction_vehicle  ON vehicle_prediction (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_prediction_comp    ON vehicle_prediction (target_component);
CREATE INDEX IF NOT EXISTS ix_vehicle_prediction_risk    ON vehicle_prediction (risk_level);
CREATE INDEX IF NOT EXISTS ix_vehicle_prediction_status  ON vehicle_prediction (status);
CREATE INDEX IF NOT EXISTS ix_vehicle_prediction_time    ON vehicle_prediction (prediction_time);

COMMENT ON TABLE  vehicle_prediction IS 'AI预测结果 — 未来风险与维护预测.';
COMMENT ON COLUMN vehicle_prediction.risk_level IS 'low | medium | high | critical';
COMMENT ON COLUMN vehicle_prediction.confidence IS '0.0-1.0 可信度';
COMMENT ON COLUMN vehicle_prediction.status IS 'active | confirmed | false_alarm | expired';


-- ----------------------------------------------------------------------------
-- 9. vehicle_soul_score_history — VSS 灵魂指数历史
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicle_soul_score_history (
    id              BIGSERIAL    PRIMARY KEY,
    vehicle_id      BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    soul_score      FLOAT        NOT NULL,       -- 0-100
    health_score    FLOAT,                        -- 健康状态 0-100
    memory_score    FLOAT,                        -- 记忆丰富度 0-100
    maintenance_score FLOAT,                      -- 维护质量 0-100
    driving_score   FLOAT,                        -- 驾驶关系 0-100
    prediction_score FLOAT,                       -- 预测稳定性 0-100

    grade           VARCHAR(20),                  -- legendary | excellent | normal | risk
    notes           TEXT,

    recorded_at     TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_soul_score_history_vehicle ON vehicle_soul_score_history (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_soul_score_history_time   ON vehicle_soul_score_history (recorded_at);

COMMENT ON TABLE vehicle_soul_score_history IS 'VSS 灵魂指数历史 — 追踪车辆灵魂的成长轨迹.';
COMMENT ON COLUMN vehicle_soul_score_history.grade IS 'legendary | excellent | normal | risk';


-- ----------------------------------------------------------------------------
-- 10. Updated-at trigger for new tables
-- ----------------------------------------------------------------------------
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'vehicle_life_state',
        'driver_profile'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_%s_updated_at ON %I; '
            'CREATE TRIGGER trg_%s_updated_at '
            'BEFORE UPDATE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION cs_set_updated_at();',
            t, t, t, t
        );
    END LOOP;
END
$$;


-- ----------------------------------------------------------------------------
-- 11. Convenience view: vehicle digital life overview
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_digital_life_overview AS
SELECT
    v.id                               AS vehicle_id,
    v.brand,
    v.model,
    v.year_                             AS year,
    v.vin,
    v.nickname,
    v.fuel_type,
    v.mileage,
    v.status                            AS vehicle_status,

    -- Digital identity
    di.vehicle_uuid                     AS soul_id,
    di.birth_time,

    -- Life state
    ls.life_stage,
    ls.health_score                    AS life_health_score,
    ls.energy_health,
    ls.mechanical_health,
    ls.software_health,
    ls.soul_score,
    ls.vehicle_age_days,

    -- Driver profile
    dp.driver_style,
    dp.aggressive_score,
    dp.comfort_score,
    dp.eco_score

FROM vehicles v
LEFT JOIN vehicle_identity di  ON di.vehicle_id = v.id
LEFT JOIN vehicle_life_state ls ON ls.vehicle_id = v.id
LEFT JOIN driver_profile dp    ON dp.vehicle_id = v.id;

COMMENT ON VIEW v_digital_life_overview IS '车辆数字生命概览 — 身份+生命状态+驾驶人格联合视图.';


-- ============================================================================
-- End of migration — TASK007-V2 Digital Life Engine
-- ============================================================================
-- Verification queries:
--   \dt vehicle_*
--   SELECT * FROM v_digital_life_overview;
--   SELECT vehicle_uuid, life_stage, soul_score FROM v_digital_life_overview;
