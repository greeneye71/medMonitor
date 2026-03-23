-- medMonitor — TimescaleDB schema initialization
-- Run once on a fresh PostgreSQL+TimescaleDB instance

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Temperature readings table
CREATE TABLE IF NOT EXISTS temperature_readings (
    id          BIGSERIAL,
    zone        VARCHAR(20)  NOT NULL,
    sensor_id   VARCHAR(50)  NOT NULL,
    temperature DECIMAL(5,2) NOT NULL,
    humidity    DECIMAL(5,2),
    battery     SMALLINT,
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

-- Convert to hypertable (TimescaleDB)
SELECT create_hypertable('temperature_readings', 'timestamp',
    if_not_exists => TRUE
);

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id             BIGSERIAL PRIMARY KEY,
    zone           VARCHAR(20)  NOT NULL,
    sensor_id      VARCHAR(50)  NOT NULL,
    temperature    DECIMAL(5,2) NOT NULL,
    level          VARCHAR(10)  NOT NULL,  -- WARNING | CRITICAL
    threshold_min  DECIMAL(5,2) NOT NULL,
    threshold_max  DECIMAL(5,2) NOT NULL,
    message        TEXT DEFAULT '',
    timestamp      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_readings_zone_time
    ON temperature_readings (zone, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_readings_sensor_time
    ON temperature_readings (sensor_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_zone_time
    ON alerts (zone, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_level
    ON alerts (level);

-- Retention policy: auto-drop data older than 365 days
SELECT add_retention_policy('temperature_readings', INTERVAL '365 days',
    if_not_exists => TRUE
);
