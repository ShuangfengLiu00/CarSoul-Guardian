-- ============================================================================
-- CarSoul Guardian — Vehicle Digital Life Record (TASK007)
-- PostgreSQL 16 + TimescaleDB migration script
-- ============================================================================
-- This script creates the complete schema for the Vehicle Digital Twin
-- Engine: vehicle identity, digital state, IoT sensor telemetry, trip
-- lifecycle, maintenance medical-record, fault history, driving-behaviour
-- profile, health snapshots, risk predictions, ownership transfers,
-- lifecycle events, alerts, and digital-twin metadata.
--
-- Time-series tables (vehicle_sensor_data, vehicle_trips) are converted to
-- TimescaleDB hypertables for high-frequency ingest and fast range scans.
--
-- Idempotent: each CREATE TABLE is guarded by IF NOT EXISTS; hypertable
-- conversion is guarded by a check on timescaledb_information.hypertables.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 0. Extensions
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- TimescaleDB is required for hypertables; install in the target DB first:
--   sudo apt install timescaledb-2-postgresql-16
--   timescaledb-tune
CREATE EXTENSION IF NOT EXISTS timescaledb;


-- ============================================================================
-- 1. users  —  vehicle owners / drivers / mechanics
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL    PRIMARY KEY,
    username        VARCHAR(64)  UNIQUE NOT NULL,
    email           VARCHAR(128) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,

    phone           VARCHAR(32),
    avatar_url      VARCHAR(512),
    display_name    VARCHAR(64),

    role            VARCHAR(32)  NOT NULL DEFAULT 'owner',  -- owner | admin | mechanic | agent

    preferences     JSONB,
    agent_settings  JSONB,

    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);
CREATE INDEX IF NOT EXISTS ix_users_email    ON users (email);

COMMENT ON TABLE  users IS 'A registered CarSoul Guardian user / vehicle owner.';
COMMENT ON COLUMN users.role IS 'owner | admin | mechanic | agent';
COMMENT ON COLUMN users.preferences IS 'JSON: theme, language, notification settings, ...';


-- ============================================================================
-- 2. vehicles  —  vehicle birth certificate (root entity)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicles (
    id                  BIGSERIAL    PRIMARY KEY,
    owner_id            BIGINT       REFERENCES users(id),

    -- ---- Basic identity ----
    brand               VARCHAR(64)  NOT NULL,
    model               VARCHAR(64)  NOT NULL,
    year_               INTEGER      NOT NULL,
    vin                 VARCHAR(32)  UNIQUE NOT NULL,
    plate_number        VARCHAR(20),
    color               VARCHAR(32),
    nickname            VARCHAR(64),

    -- ---- Powertrain ----
    engine_type         VARCHAR(64),
    fuel_type           VARCHAR(32)  NOT NULL DEFAULT 'gasoline',  -- gasoline | diesel | hybrid | electric | plug_in_hybrid
    displacement        DOUBLE PRECISION,  -- L
    battery_capacity    DOUBLE PRECISION,  -- kWh

    -- ---- Live status ----
    mileage             INTEGER      NOT NULL DEFAULT 0,
    status              VARCHAR(32)  NOT NULL DEFAULT 'active',    -- active | inactive | sold | scrapped

    -- ---- Purchase / dealer ----
    purchase_date       DATE,
    purchase_price      DOUBLE PRECISION,
    dealer              VARCHAR(128),

    -- ---- Insurance ----
    insurance_company   VARCHAR(128),
    insurance_policy_no VARCHAR(64),
    insurance_expiry    DATE,

    -- ---- Registration / inspection ----
    registration_date   DATE,
    inspection_expiry   DATE,

    -- ---- Digital twin linkage ----
    twin_model_id       VARCHAR(128),
    twin_last_sync      TIMESTAMP,

    -- ---- Misc ----
    avatar_url          VARCHAR(512),
    notes               TEXT,

    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- NOTE: SQLAlchemy ORM maps Vehicle.year -> column "year" (quoted keyword).
-- For the hand-written DDL we use year_ and add a view/alias below.
-- If you prefer to keep the column name identical to the ORM, replace
-- `year_` with `"year"` (quoted) throughout this script.

CREATE INDEX IF NOT EXISTS ix_vehicles_owner_id ON vehicles (owner_id);
CREATE INDEX IF NOT EXISTS ix_vehicles_vin      ON vehicles (vin);
CREATE INDEX IF NOT EXISTS ix_vehicles_status   ON vehicles (status);

COMMENT ON TABLE  vehicles IS 'A single vehicle — the root entity of the digital-life archive.';
COMMENT ON COLUMN vehicles.fuel_type IS 'gasoline | diesel | hybrid | electric | plug_in_hybrid';
COMMENT ON COLUMN vehicles.status    IS 'active | inactive | sold | scrapped';


-- ============================================================================
-- 3. vehicle_digital_states  —  real-time current digital state (1:1)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_digital_states (
    id                  BIGSERIAL    PRIMARY KEY,
    vehicle_id          BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    -- ---- Sub-system health (0-100) ----
    engine_health       DOUBLE PRECISION,
    battery_health      DOUBLE PRECISION,
    brake_health        DOUBLE PRECISION,
    tire_health         DOUBLE PRECISION,
    body_health         DOUBLE PRECISION,
    electronics_health  DOUBLE PRECISION,

    -- ---- Overall ----
    overall_score       DOUBLE PRECISION,
    status              VARCHAR(30)  NOT NULL DEFAULT 'GOOD',  -- GOOD | WARNING | DANGER | END_OF_LIFE

    -- ---- Live telemetry snapshot ----
    temperature         DOUBLE PRECISION,  -- C
    mileage             BIGINT,
    fuel_level          DOUBLE PRECISION,  -- % or kWh remaining
    location            JSONB,             -- {"lat": ..., "lng": ..., "name": ...}

    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_vehicle_digital_states_vehicle UNIQUE (vehicle_id)
);

CREATE INDEX IF NOT EXISTS ix_vehicle_digital_states_vehicle_id ON vehicle_digital_states (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_digital_states_status     ON vehicle_digital_states (status);

COMMENT ON TABLE  vehicle_digital_states IS 'The real-time current digital state of a single vehicle.';
COMMENT ON COLUMN vehicle_digital_states.status IS 'GOOD | WARNING | DANGER | END_OF_LIFE';
COMMENT ON COLUMN vehicle_digital_states.location IS 'JSONB: {"lat": ..., "lng": ..., "name": ...}';


-- ============================================================================
-- 4. vehicle_sensor_data  —  high-frequency IoT telemetry (TIME-SERIES)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_sensor_data (
    id            BIGSERIAL    PRIMARY KEY,
    vehicle_id    BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    sensor_type   VARCHAR(50)  NOT NULL,  -- engine_temp | battery_voltage | tire_pressure | ...
    sensor_value  DOUBLE PRECISION NOT NULL,
    unit          VARCHAR(20),
    meta          JSONB,                  -- {"position": "FL"} / {"channel": 1}

    created_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_sensor_data_vehicle_id  ON vehicle_sensor_data (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_sensor_data_sensor_type ON vehicle_sensor_data (sensor_type);
CREATE INDEX IF NOT EXISTS ix_vehicle_sensor_data_created_at  ON vehicle_sensor_data (created_at);

-- Composite index for the most common range scan: "latest N readings of a
-- given sensor type for a vehicle".
CREATE INDEX IF NOT EXISTS ix_vehicle_sensor_data_vtype_time
    ON vehicle_sensor_data (vehicle_id, sensor_type, created_at DESC);

COMMENT ON TABLE  vehicle_sensor_data IS 'IoT sensor readings — high-frequency time-series (TimescaleDB hypertable).';
COMMENT ON COLUMN vehicle_sensor_data.sensor_type IS 'engine_temp | battery_voltage | tire_pressure | coolant_temp | rpm | speed | fuel_level | oil_pressure | intake_air_temp | ...';
COMMENT ON COLUMN vehicle_sensor_data.meta IS 'JSONB: optional metadata, e.g. {"position":"FL"} for tyre pressure.';


-- ============================================================================
-- 5. vehicle_trips  —  every journey (TIME-SERIES-friendly)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_trips (
    id                          BIGSERIAL    PRIMARY KEY,
    vehicle_id                  BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    driver_id                   BIGINT       REFERENCES users(id),

    start_time                  TIMESTAMP    NOT NULL,
    end_time                    TIMESTAMP,

    distance                    DOUBLE PRECISION NOT NULL DEFAULT 0.0,  -- km
    average_speed               DOUBLE PRECISION,  -- km/h
    max_speed                   DOUBLE PRECISION,  -- km/h

    energy_consumption          DOUBLE PRECISION,  -- L (fuel) or kWh (electric)

    road_condition              VARCHAR(32),  -- urban | highway | suburban | mountain | rural
    weather                     VARCHAR(32),  -- sunny | cloudy | rainy | snowy | foggy

    harsh_acceleration_count    INTEGER      NOT NULL DEFAULT 0,
    harsh_braking_count         INTEGER      NOT NULL DEFAULT 0,
    overspeed_count             INTEGER      NOT NULL DEFAULT 0,

    start_location              JSONB,  -- {"lat": ..., "lng": ..., "name": ...}
    end_location                JSONB,

    notes                       VARCHAR(256),

    created_at                  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_trips_vehicle_id ON vehicle_trips (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_trips_driver_id  ON vehicle_trips (driver_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_trips_start_time ON vehicle_trips (start_time);

COMMENT ON TABLE  vehicle_trips IS 'A single driving trip for a vehicle.';
COMMENT ON COLUMN vehicle_trips.road_condition IS 'urban | highway | suburban | mountain | rural';
COMMENT ON COLUMN vehicle_trips.weather IS 'sunny | cloudy | rainy | snowy | foggy';


-- ============================================================================
-- 6. vehicle_maintenance_records  —  vehicle medical record (history)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_maintenance_records (
    id                          BIGSERIAL    PRIMARY KEY,
    vehicle_id                  BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    maintenance_type            VARCHAR(32)  NOT NULL,  -- routine | repair | emergency | inspection | recall
    category                    VARCHAR(64)  NOT NULL,  -- 机油更换 | 刹车片 | 轮胎 | 电池 | 滤芯 | ...
    title                       VARCHAR(128) NOT NULL,
    description                 TEXT,

    maintenance_date            DATE         NOT NULL,
    mileage                     BIGINT,

    cost                        DOUBLE PRECISION,

    service_provider            VARCHAR(128),
    technician                  VARCHAR(64),

    parts                       JSONB,  -- [{name, quantity, unit_price}]

    next_maintenance_date       DATE,
    next_maintenance_mileage    BIGINT,

    created_at                  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_maintenance_records_vehicle_id        ON vehicle_maintenance_records (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_maintenance_records_maintenance_date  ON vehicle_maintenance_records (maintenance_date);

COMMENT ON TABLE  vehicle_maintenance_records IS 'A completed maintenance / repair event.';
COMMENT ON COLUMN vehicle_maintenance_records.maintenance_type IS 'routine | repair | emergency | inspection | recall';
COMMENT ON COLUMN vehicle_maintenance_records.parts IS 'JSONB array: [{name, quantity, unit_price}]';


-- ============================================================================
-- 7. vehicle_maintenance_schedules  —  recurring maintenance rules
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_maintenance_schedules (
    id                  BIGSERIAL    PRIMARY KEY,
    vehicle_id          BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    item_name           VARCHAR(64)  NOT NULL,
    category            VARCHAR(64)  NOT NULL,

    interval_km         INTEGER,
    interval_days       INTEGER,

    last_mileage        INTEGER,
    last_date           DATE,

    next_due_km         INTEGER,
    next_due_date       DATE,

    priority            VARCHAR(16)  NOT NULL DEFAULT 'medium',  -- low | medium | high
    status              VARCHAR(16)  NOT NULL DEFAULT 'pending', -- pending | due | overdue | done | paused

    notes               TEXT,

    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_maintenance_schedules_vehicle_id ON vehicle_maintenance_schedules (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_maintenance_schedules_status     ON vehicle_maintenance_schedules (status);

COMMENT ON TABLE  vehicle_maintenance_schedules IS 'A recurring maintenance rule for a vehicle.';
COMMENT ON COLUMN vehicle_maintenance_schedules.priority IS 'low | medium | high';
COMMENT ON COLUMN vehicle_maintenance_schedules.status   IS 'pending | due | overdue | done | paused';


-- ============================================================================
-- 8. vehicle_fault_logs  —  vehicle disease history
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_fault_logs (
    id                          BIGSERIAL    PRIMARY KEY,
    vehicle_id                  BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    fault_code                  VARCHAR(50)  NOT NULL,  -- OBD-II DTC: P0420, P0301, B1001, U0100
    fault_level                 VARCHAR(20)  NOT NULL DEFAULT 'medium',  -- low | medium | high | critical

    description                 TEXT,
    system                      VARCHAR(32),  -- engine | transmission | brake | battery | tire | electronics | body | other

    repair_status               VARCHAR(30)  NOT NULL DEFAULT 'active',  -- active | diagnosing | repairing | resolved | ignored

    mileage                     BIGINT,

    occur_time                  TIMESTAMP    NOT NULL DEFAULT NOW(),
    resolved_time               TIMESTAMP,

    maintenance_record_id       BIGINT       REFERENCES vehicle_maintenance_records(id) ON DELETE SET NULL,

    created_at                  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_fault_logs_vehicle_id    ON vehicle_fault_logs (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_fault_logs_fault_code    ON vehicle_fault_logs (fault_code);
CREATE INDEX IF NOT EXISTS ix_vehicle_fault_logs_fault_level   ON vehicle_fault_logs (fault_level);
CREATE INDEX IF NOT EXISTS ix_vehicle_fault_logs_repair_status ON vehicle_fault_logs (repair_status);
CREATE INDEX IF NOT EXISTS ix_vehicle_fault_logs_occur_time    ON vehicle_fault_logs (occur_time);

COMMENT ON TABLE  vehicle_fault_logs IS 'A single fault occurrence on a vehicle (OBD DTC).';
COMMENT ON COLUMN vehicle_fault_logs.fault_code    IS 'OBD-II DTC code, e.g. P0420, P0301, B1001, U0100';
COMMENT ON COLUMN vehicle_fault_logs.fault_level   IS 'low | medium | high | critical';
COMMENT ON COLUMN vehicle_fault_logs.system        IS 'engine | transmission | brake | battery | tire | electronics | body | other';
COMMENT ON COLUMN vehicle_fault_logs.repair_status IS 'active | diagnosing | repairing | resolved | ignored';


-- ============================================================================
-- 9. vehicle_driving_behaviors  —  daily driving-behaviour aggregation
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_driving_behaviors (
    id                          BIGSERIAL    PRIMARY KEY,
    vehicle_id                  BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    record_date                 DATE         NOT NULL,

    trip_count                  INTEGER      NOT NULL DEFAULT 0,
    total_distance              DOUBLE PRECISION NOT NULL DEFAULT 0.0,  -- km
    total_duration              INTEGER      NOT NULL DEFAULT 0,  -- minutes
    avg_speed                   DOUBLE PRECISION,  -- km/h
    max_speed                   DOUBLE PRECISION,  -- km/h

    safety_score                INTEGER,  -- 0-100
    eco_score                   INTEGER,  -- 0-100

    harsh_acceleration_count    INTEGER      NOT NULL DEFAULT 0,
    harsh_braking_count         INTEGER      NOT NULL DEFAULT 0,
    sharp_turn_count            INTEGER      NOT NULL DEFAULT 0,
    overspeed_count             INTEGER      NOT NULL DEFAULT 0,
    idle_duration               INTEGER      NOT NULL DEFAULT 0,  -- minutes

    fuel_consumption            DOUBLE PRECISION,  -- L or kWh
    energy_efficiency           DOUBLE PRECISION,  -- km/L or km/kWh

    created_at                  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_driving_behaviors_vehicle_id  ON vehicle_driving_behaviors (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_driving_behaviors_record_date ON vehicle_driving_behaviors (record_date);

COMMENT ON TABLE vehicle_driving_behaviors IS 'A daily driving-behaviour summary for a vehicle.';


-- ============================================================================
-- 10. vehicle_health_snapshots  —  periodic health assessment
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_health_snapshots (
    id                  BIGSERIAL    PRIMARY KEY,
    vehicle_id          BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    health_score        INTEGER      NOT NULL,  -- 0-100
    mileage             BIGINT       NOT NULL,

    engine_score        INTEGER,
    brake_score         INTEGER,
    tire_score          INTEGER,
    battery_score       INTEGER,
    body_score          INTEGER,
    electronics_score   INTEGER,

    summary             TEXT,

    source              VARCHAR(32)  NOT NULL DEFAULT 'manual',  -- manual | obd | scheduled | agent

    snapshot_time       TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_health_snapshots_vehicle_id    ON vehicle_health_snapshots (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_health_snapshots_snapshot_time ON vehicle_health_snapshots (snapshot_time);

COMMENT ON TABLE  vehicle_health_snapshots IS 'A periodic health assessment for a vehicle.';
COMMENT ON COLUMN vehicle_health_snapshots.source IS 'manual | obd | scheduled | agent';


-- ============================================================================
-- 11. vehicle_health_items  —  per-item risk breakdown within a snapshot
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_health_items (
    id              BIGSERIAL    PRIMARY KEY,
    snapshot_id     BIGINT       NOT NULL REFERENCES vehicle_health_snapshots(id) ON DELETE CASCADE,
    vehicle_id      BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    category        VARCHAR(32)  NOT NULL,  -- engine | brake | tire | battery | body | electronics | fluid | other
    item_name       VARCHAR(64)  NOT NULL,

    level           VARCHAR(16)  NOT NULL,  -- ok | info | warning | critical
    score           INTEGER,  -- 0-100

    detail          TEXT,
    recommendation  TEXT
);

CREATE INDEX IF NOT EXISTS ix_vehicle_health_items_snapshot_id ON vehicle_health_items (snapshot_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_health_items_vehicle_id  ON vehicle_health_items (vehicle_id);

COMMENT ON TABLE  vehicle_health_items IS 'An individual check-item within a health snapshot.';
COMMENT ON COLUMN vehicle_health_items.category IS 'engine | brake | tire | battery | body | electronics | fluid | other';
COMMENT ON COLUMN vehicle_health_items.level    IS 'ok | info | warning | critical';


-- ============================================================================
-- 12. risk_predictions  —  AI risk-prediction runs + closed-loop feedback
-- ============================================================================
CREATE TABLE IF NOT EXISTS risk_predictions (
    id                          BIGSERIAL    PRIMARY KEY,
    vehicle_id                  BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    triggered_by                VARCHAR(16)  NOT NULL DEFAULT 'user',  -- patrol | user | alert | scheduled

    is_normal                   BOOLEAN      NOT NULL DEFAULT FALSE,
    predicted_level             VARCHAR(16)  NOT NULL DEFAULT 'info',  -- info | warning | urgent
    predicted_probability       INTEGER,
    predicted_eta_hours         INTEGER,
    primary_type                VARCHAR(64),
    root_cause                  VARCHAR(256),
    trend                       VARCHAR(32),
    explanation                 TEXT,
    actions_hint                JSONB,
    anomalies_count             INTEGER      NOT NULL DEFAULT 0,

    trace_log                   JSONB,

    alert_id                    BIGINT       REFERENCES vehicle_alerts(id) ON DELETE SET NULL,

    status                      VARCHAR(16)  NOT NULL DEFAULT 'open',  -- open | acknowledged | resolved | expired
    acknowledged_at             TIMESTAMP,

    actual_outcome              VARCHAR(16),  -- confirmed | false_alarm | no_event | partial
    outcome_notes               TEXT,
    accuracy                    DOUBLE PRECISION,  -- 0.0 - 1.0
    resolved_at                 TIMESTAMP,

    created_at                  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_risk_predictions_vehicle_id      ON risk_predictions (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_risk_predictions_triggered_by   ON risk_predictions (triggered_by);
CREATE INDEX IF NOT EXISTS ix_risk_predictions_predicted_level ON risk_predictions (predicted_level);
CREATE INDEX IF NOT EXISTS ix_risk_predictions_status         ON risk_predictions (status);
CREATE INDEX IF NOT EXISTS ix_risk_predictions_created_at     ON risk_predictions (created_at);

COMMENT ON TABLE  risk_predictions IS 'A single risk-prediction run and its eventual outcome (closed loop).';
COMMENT ON COLUMN risk_predictions.triggered_by     IS 'patrol | user | alert | scheduled';
COMMENT ON COLUMN risk_predictions.predicted_level  IS 'info | warning | urgent';
COMMENT ON COLUMN risk_predictions.status           IS 'open | acknowledged | resolved | expired';
COMMENT ON COLUMN risk_predictions.actual_outcome   IS 'confirmed | false_alarm | no_event | partial';
COMMENT ON COLUMN risk_predictions.accuracy         IS '0.0 - 1.0; computed when feedback is submitted';


-- ============================================================================
-- 13. vehicle_alerts  —  user-facing notifications
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_alerts (
    id                  BIGSERIAL    PRIMARY KEY,
    vehicle_id          BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    alert_type          VARCHAR(32)  NOT NULL,  -- maintenance | health | behavior | insurance | inspection | system
    level               VARCHAR(16)  NOT NULL,  -- info | warning | critical
    category            VARCHAR(64),

    title               VARCHAR(128) NOT NULL,
    detail              TEXT,
    recommendation      TEXT,

    status              VARCHAR(16)  NOT NULL DEFAULT 'active',  -- active | acknowledged | resolved
    acknowledged_at     TIMESTAMP,
    resolved_at         TIMESTAMP,

    triggered_at        TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_alerts_vehicle_id   ON vehicle_alerts (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_alerts_alert_type   ON vehicle_alerts (alert_type);
CREATE INDEX IF NOT EXISTS ix_vehicle_alerts_level        ON vehicle_alerts (level);
CREATE INDEX IF NOT EXISTS ix_vehicle_alerts_status       ON vehicle_alerts (status);
CREATE INDEX IF NOT EXISTS ix_vehicle_alerts_triggered_at ON vehicle_alerts (triggered_at);

COMMENT ON TABLE  vehicle_alerts IS 'A single alert attached to a vehicle.';
COMMENT ON COLUMN vehicle_alerts.alert_type IS 'maintenance | health | behavior | insurance | inspection | system';
COMMENT ON COLUMN vehicle_alerts.level      IS 'info | warning | critical';
COMMENT ON COLUMN vehicle_alerts.status     IS 'active | acknowledged | resolved';


-- ============================================================================
-- 14. vehicle_ownership_records  —  transfer history
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_ownership_records (
    id                      BIGSERIAL    PRIMARY KEY,
    vehicle_id              BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    owner_id                BIGINT       REFERENCES users(id),
    owner_name              VARCHAR(64),

    start_date              DATE         NOT NULL,
    end_date                DATE,

    transfer_type           VARCHAR(32)  NOT NULL DEFAULT 'purchase',  -- purchase | sale | gift | inheritance

    purchase_price          DOUBLE PRECISION,
    sale_price              DOUBLE PRECISION,
    mileage_at_transfer     BIGINT,

    notes                   TEXT,

    created_at              TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_ownership_records_vehicle_id ON vehicle_ownership_records (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_ownership_records_owner_id   ON vehicle_ownership_records (owner_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_ownership_records_start_date ON vehicle_ownership_records (start_date);

COMMENT ON TABLE  vehicle_ownership_records IS 'An ownership period for a vehicle.';
COMMENT ON COLUMN vehicle_ownership_records.transfer_type IS 'purchase | sale | gift | inheritance';


-- ============================================================================
-- 15. vehicle_lifecycle_events  —  timeline of the vehicle's digital life
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_lifecycle_events (
    id              BIGSERIAL    PRIMARY KEY,
    vehicle_id      BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    event_type      VARCHAR(32)  NOT NULL,  -- purchase | transfer | accident | repair | maintenance | inspection | insurance | registration | custom

    title           VARCHAR(128) NOT NULL,
    description     TEXT,

    event_date      DATE         NOT NULL,
    mileage         BIGINT,

    cost            DOUBLE PRECISION,
    location        VARCHAR(256),

    severity        VARCHAR(16),  -- info | minor | moderate | major | critical

    extra_data      JSONB,

    created_at      TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vehicle_lifecycle_events_vehicle_id  ON vehicle_lifecycle_events (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_lifecycle_events_event_type  ON vehicle_lifecycle_events (event_type);
CREATE INDEX IF NOT EXISTS ix_vehicle_lifecycle_events_event_date  ON vehicle_lifecycle_events (event_date);

COMMENT ON TABLE  vehicle_lifecycle_events IS 'A single point on the vehicle life timeline.';
COMMENT ON COLUMN vehicle_lifecycle_events.event_type IS 'purchase | transfer | accident | repair | maintenance | inspection | insurance | registration | custom';
COMMENT ON COLUMN vehicle_lifecycle_events.severity   IS 'info | minor | moderate | major | critical';


-- ============================================================================
-- 16. vehicle_digital_twins  —  digital-twin metadata (1:1)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vehicle_digital_twins (
    id              BIGSERIAL    PRIMARY KEY,
    vehicle_id      BIGINT       NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,

    model_version   VARCHAR(32)  NOT NULL DEFAULT '1.0',
    model_url       VARCHAR(512),

    telemetry       JSONB,
    config          JSONB,

    sync_status     VARCHAR(16)  NOT NULL DEFAULT 'pending',  -- pending | syncing | synced | error
    last_sync_at    TIMESTAMP,
    sync_frequency  VARCHAR(16)  NOT NULL DEFAULT 'realtime', -- realtime | hourly | daily

    notes           TEXT,

    created_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_vehicle_digital_twins_vehicle UNIQUE (vehicle_id)
);

CREATE INDEX IF NOT EXISTS ix_vehicle_digital_twins_vehicle_id  ON vehicle_digital_twins (vehicle_id);
CREATE INDEX IF NOT EXISTS ix_vehicle_digital_twins_sync_status ON vehicle_digital_twins (sync_status);

COMMENT ON TABLE  vehicle_digital_twins IS 'Digital-twin state for a single vehicle.';
COMMENT ON COLUMN vehicle_digital_twins.sync_status    IS 'pending | syncing | synced | error';
COMMENT ON COLUMN vehicle_digital_twins.sync_frequency IS 'realtime | hourly | daily';


-- ============================================================================
-- 17. TimescaleDB hypertables  —  convert time-series tables
-- ============================================================================
-- vehicle_sensor_data and vehicle_trips are high-frequency ingest tables;
-- convert them to TimescaleDB hypertables partitioned by time.

DO $$
BEGIN
    -- vehicle_sensor_data -> hypertable on created_at, chunk_interval 7 days
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'vehicle_sensor_data'
    ) THEN
        PERFORM create_hypertable(
            'vehicle_sensor_data',
            'created_at',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists       => TRUE
        );
    END IF;

    -- vehicle_trips -> hypertable on start_time, chunk_interval 30 days
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'vehicle_trips'
    ) THEN
        PERFORM create_hypertable(
            'vehicle_trips',
            'start_time',
            chunk_time_interval => INTERVAL '30 days',
            if_not_exists       => TRUE
        );
    END IF;
END
$$;


-- ============================================================================
-- 18. Retention policies  —  auto-drop old time-series chunks
-- ============================================================================
-- Keep sensor readings for 1 year, raw trips for 5 years. Adjust as needed.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.jobs
        WHERE proc_name = 'policy_retention'
          AND hypertable_name = 'vehicle_sensor_data'
    ) THEN
        PERFORM add_retention_policy('vehicle_sensor_data', INTERVAL '1 year');
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.jobs
        WHERE proc_name = 'policy_retention'
          AND hypertable_name = 'vehicle_trips'
    ) THEN
        PERFORM add_retention_policy('vehicle_trips', INTERVAL '5 years');
    END IF;
END
$$;


-- ============================================================================
-- 19. Continuous aggregates  —  pre-aggregated views for dashboards
-- ============================================================================
-- Hourly average sensor reading per vehicle — speeds up the dashboard
-- "latest sensor" panel and the health-trend chart.

CREATE MATERIALIZED VIEW IF NOT EXISTS vehicle_sensor_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', created_at) AS bucket,
    vehicle_id,
    sensor_type,
    AVG(sensor_value)   AS avg_value,
    MIN(sensor_value)   AS min_value,
    MAX(sensor_value)   AS max_value,
    COUNT(*)            AS sample_count
FROM vehicle_sensor_data
GROUP BY bucket, vehicle_id, sensor_type
WITH NO DATA;

-- Refresh policy: every 1 hour, refresh the last 3 hours of data.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.jobs
        WHERE proc_name = 'policy_refresh_continuous_aggregate'
          AND hypertable_name = 'vehicle_sensor_hourly'
    ) THEN
        PERFORM add_continuous_aggregate_policy(
            'vehicle_sensor_hourly',
            start_offset      => INTERVAL '3 hours',
            end_offset        => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour'
        );
    END IF;
END
$$;


-- ============================================================================
-- 20. Updated-at triggers  —  keep updated_at columns fresh
-- ============================================================================
-- SQLAlchemy ORM sets onupdate=func.now() but raw SQL inserts/updates bypass
-- that; install a trigger to be safe.

CREATE OR REPLACE FUNCTION cs_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'users',
        'vehicles',
        'vehicle_digital_states',
        'vehicle_maintenance_schedules',
        'risk_predictions',
        'vehicle_digital_twins'
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


-- ============================================================================
-- 21. Seed-friendly helpers (optional, dev only)
-- ============================================================================
-- A convenience view: latest digital state + vehicle profile, used by the
-- dashboard "vehicles overview" panel and the AI agent.

CREATE OR REPLACE VIEW v_vehicle_overview AS
SELECT
    v.id                                   AS vehicle_id,
    v.brand,
    v.model,
    v.year_                                AS year,
    v.vin,
    v.nickname,
    v.fuel_type,
    v.color,
    v.mileage,
    v.status                               AS vehicle_status,
    v.avatar_url,
    COALESCE(s.overall_score, 0)           AS health_score,
    COALESCE(s.status, 'GOOD')             AS health_status,
    s.engine_health,
    s.battery_health,
    s.brake_health,
    s.tire_health,
    s.temperature,
    s.fuel_level,
    s.location,
    s.updated_at                           AS state_updated_at
FROM vehicles v
LEFT JOIN vehicle_digital_states s ON s.vehicle_id = v.id;

COMMENT ON VIEW v_vehicle_overview IS 'Convenience join of vehicles + latest digital state for dashboards.';


-- ============================================================================
-- End of migration
-- ============================================================================
-- Verification queries (run manually after applying):
--
--   SELECT * FROM timescaledb_information.hypertables;
--   SELECT * FROM timescaledb_information.jobs;
--   \d+ vehicle_sensor_data
--   \d+ vehicle_trips
--   SELECT count(*) FROM v_vehicle_overview;
