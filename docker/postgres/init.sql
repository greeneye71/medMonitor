-- medMonitor — TimescaleDB schema initialization
-- Runs automatically on first container start via /docker-entrypoint-initdb.d/

CREATE TABLE IF NOT EXISTS temperature_readings (
    id          BIGSERIAL,
    zone        TEXT             NOT NULL,
    sensor_id   TEXT             NOT NULL,
    temperature DOUBLE PRECISION NOT NULL,
    humidity    DOUBLE PRECISION,
    battery     INTEGER,
    timestamp   TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('temperature_readings', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_readings_sensor_ts
    ON temperature_readings (sensor_id, timestamp DESC);


CREATE TABLE IF NOT EXISTS alerts (
    id            TEXT             NOT NULL DEFAULT gen_random_uuid()::TEXT,
    zone          TEXT             NOT NULL,
    sensor_id     TEXT             NOT NULL,
    temperature   DOUBLE PRECISION NOT NULL,
    level         TEXT             NOT NULL,
    threshold_min DOUBLE PRECISION NOT NULL,
    threshold_max DOUBLE PRECISION NOT NULL,
    message       TEXT             NOT NULL DEFAULT '',
    timestamp     TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    resolved      BOOLEAN          NOT NULL DEFAULT FALSE,
    PRIMARY KEY   (id, timestamp)
);

SELECT create_hypertable('alerts', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_alerts_level_ts
    ON alerts (level, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_sensor_ts
    ON alerts (sensor_id, timestamp DESC);
