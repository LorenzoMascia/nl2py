-- TimescaleDB Initialization Script for NL2Py
-- This script creates sample time-series data for testing

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ==============================================
-- Example 1: IoT Sensor Data
-- ==============================================
CREATE TABLE sensor_data (
    time TIMESTAMPTZ NOT NULL,
    sensor_id INTEGER,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    pressure DOUBLE PRECISION,
    location TEXT
);

-- Convert to hypertable with 1-day chunks
SELECT create_hypertable('sensor_data', 'time', chunk_time_interval => INTERVAL '1 day');

-- Insert sample sensor data
INSERT INTO sensor_data VALUES
    (NOW() - INTERVAL '7 days', 1, 22.5, 45.0, 1013.25, 'Office'),
    (NOW() - INTERVAL '6 days', 1, 23.0, 46.5, 1012.80, 'Office'),
    (NOW() - INTERVAL '5 days', 1, 22.8, 45.8, 1013.00, 'Office'),
    (NOW() - INTERVAL '4 days', 1, 23.2, 47.0, 1013.50, 'Office'),
    (NOW() - INTERVAL '3 days', 1, 23.5, 47.5, 1013.75, 'Office'),
    (NOW() - INTERVAL '2 days', 1, 24.0, 48.0, 1014.00, 'Office'),
    (NOW() - INTERVAL '1 day', 1, 24.2, 48.5, 1014.25, 'Office'),
    (NOW() - INTERVAL '12 hours', 1, 24.5, 49.0, 1014.50, 'Office'),
    (NOW() - INTERVAL '6 hours', 1, 24.8, 49.5, 1014.75, 'Office'),
    (NOW() - INTERVAL '3 hours', 1, 25.0, 50.0, 1015.00, 'Office'),
    (NOW() - INTERVAL '1 hour', 1, 25.2, 50.2, 1015.10, 'Office'),
    (NOW() - INTERVAL '30 minutes', 1, 25.3, 50.5, 1015.20, 'Office'),
    (NOW(), 1, 25.5, 50.8, 1015.30, 'Office');

-- Additional sensors
INSERT INTO sensor_data VALUES
    (NOW() - INTERVAL '1 hour', 2, 20.0, 55.0, 1013.00, 'Warehouse'),
    (NOW() - INTERVAL '30 minutes', 2, 20.5, 54.5, 1013.10, 'Warehouse'),
    (NOW(), 2, 21.0, 54.0, 1013.20, 'Warehouse');

-- Create continuous aggregate for hourly averages
CREATE MATERIALIZED VIEW sensor_data_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', time) AS bucket,
       sensor_id,
       AVG(temperature) as avg_temp,
       AVG(humidity) as avg_humidity,
       AVG(pressure) as avg_pressure,
       MAX(temperature) as max_temp,
       MIN(temperature) as min_temp
FROM sensor_data
GROUP BY bucket, sensor_id
WITH DATA;

-- Add automatic refresh policy (refresh every 30 minutes)
SELECT add_continuous_aggregate_policy('sensor_data_hourly',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 minutes');

-- ==============================================
-- Example 2: Application Metrics (APM)
-- ==============================================
CREATE TABLE app_metrics (
    time TIMESTAMPTZ NOT NULL,
    service_name TEXT,
    endpoint TEXT,
    response_time_ms INTEGER,
    status_code INTEGER,
    user_id TEXT
);

-- Convert to hypertable with 1-hour chunks (high frequency data)
SELECT create_hypertable('app_metrics', 'time', chunk_time_interval => INTERVAL '1 hour');

-- Insert sample metrics
INSERT INTO app_metrics VALUES
    (NOW() - INTERVAL '2 hours', 'api-service', '/users', 45, 200, 'user123'),
    (NOW() - INTERVAL '2 hours', 'api-service', '/orders', 120, 200, 'user456'),
    (NOW() - INTERVAL '2 hours', 'api-service', '/products', 80, 200, 'user789'),
    (NOW() - INTERVAL '1 hour', 'api-service', '/users', 52, 200, 'user123'),
    (NOW() - INTERVAL '1 hour', 'api-service', '/orders', 5000, 500, 'user456'),
    (NOW() - INTERVAL '1 hour', 'api-service', '/products', 75, 200, 'user789'),
    (NOW() - INTERVAL '30 minutes', 'api-service', '/users', 48, 200, 'user111'),
    (NOW() - INTERVAL '30 minutes', 'api-service', '/orders', 110, 200, 'user222'),
    (NOW() - INTERVAL '30 minutes', 'web-service', '/home', 30, 200, 'user333'),
    (NOW() - INTERVAL '15 minutes', 'api-service', '/users', 50, 200, 'user444'),
    (NOW() - INTERVAL '15 minutes', 'web-service', '/home', 28, 200, 'user555'),
    (NOW() - INTERVAL '5 minutes', 'api-service', '/users', 46, 200, 'user666'),
    (NOW() - INTERVAL '5 minutes', 'web-service', '/home', 32, 200, 'user777'),
    (NOW(), 'api-service', '/users', 44, 200, 'user888');

-- Create continuous aggregate for 5-minute performance summary
CREATE MATERIALIZED VIEW app_metrics_5min
WITH (timescaledb.continuous) AS
SELECT time_bucket('5 minutes', time) AS bucket,
       service_name,
       endpoint,
       AVG(response_time_ms) as avg_response,
       MAX(response_time_ms) as max_response,
       MIN(response_time_ms) as min_response,
       COUNT(*) as request_count,
       COUNT(*) FILTER (WHERE status_code >= 500) as error_count,
       COUNT(*) FILTER (WHERE status_code >= 400 AND status_code < 500) as client_error_count
FROM app_metrics
GROUP BY bucket, service_name, endpoint
WITH DATA;

-- Add automatic refresh policy
SELECT add_continuous_aggregate_policy('app_metrics_5min',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes');

-- ==============================================
-- Example 3: Stock Market Data
-- ==============================================
CREATE TABLE stock_prices (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT
);

-- Convert to hypertable with space partitioning
SELECT create_hypertable('stock_prices', 'time',
    chunk_time_interval => INTERVAL '1 week',
    partitioning_column => 'symbol',
    number_partitions => 4);

-- Insert sample stock data
INSERT INTO stock_prices VALUES
    (NOW() - INTERVAL '5 days', 'AAPL', 150.0, 152.5, 149.0, 151.5, 50000000),
    (NOW() - INTERVAL '4 days', 'AAPL', 151.5, 153.0, 150.5, 152.0, 45000000),
    (NOW() - INTERVAL '3 days', 'AAPL', 152.0, 154.0, 151.0, 153.5, 48000000),
    (NOW() - INTERVAL '2 days', 'AAPL', 153.5, 155.0, 152.5, 154.0, 52000000),
    (NOW() - INTERVAL '1 day', 'AAPL', 154.0, 156.0, 153.0, 155.5, 55000000),
    (NOW(), 'AAPL', 155.5, 157.0, 154.5, 156.0, 50000000),
    (NOW() - INTERVAL '5 days', 'GOOGL', 2800.0, 2850.0, 2780.0, 2820.0, 1000000),
    (NOW() - INTERVAL '4 days', 'GOOGL', 2820.0, 2860.0, 2800.0, 2840.0, 1100000),
    (NOW() - INTERVAL '3 days', 'GOOGL', 2840.0, 2880.0, 2820.0, 2860.0, 1050000),
    (NOW() - INTERVAL '2 days', 'GOOGL', 2860.0, 2900.0, 2840.0, 2880.0, 1200000),
    (NOW() - INTERVAL '1 day', 'GOOGL', 2880.0, 2920.0, 2860.0, 2900.0, 1150000),
    (NOW(), 'GOOGL', 2900.0, 2940.0, 2880.0, 2920.0, 1100000);

-- Create daily OHLCV continuous aggregate
CREATE MATERIALIZED VIEW stock_prices_daily
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 day', time) AS bucket,
       symbol,
       FIRST(open, time) as open,
       MAX(high) as high,
       MIN(low) as low,
       LAST(close, time) as close,
       SUM(volume) as total_volume
FROM stock_prices
GROUP BY bucket, symbol
WITH DATA;

-- ==============================================
-- Example 4: Server Monitoring Logs
-- ==============================================
CREATE TABLE server_logs (
    time TIMESTAMPTZ NOT NULL,
    hostname TEXT,
    log_level TEXT,
    cpu_percent DOUBLE PRECISION,
    memory_percent DOUBLE PRECISION,
    disk_usage_gb DOUBLE PRECISION,
    network_in_mbps DOUBLE PRECISION,
    network_out_mbps DOUBLE PRECISION
);

-- Convert to hypertable
SELECT create_hypertable('server_logs', 'time', chunk_time_interval => INTERVAL '1 day');

-- Insert sample server monitoring data
INSERT INTO server_logs VALUES
    (NOW() - INTERVAL '1 hour', 'server1', 'INFO', 45.5, 62.3, 250.5, 15.2, 8.5),
    (NOW() - INTERVAL '55 minutes', 'server1', 'INFO', 48.2, 63.1, 250.6, 16.1, 9.2),
    (NOW() - INTERVAL '50 minutes', 'server1', 'WARN', 75.8, 78.5, 250.8, 25.5, 15.8),
    (NOW() - INTERVAL '45 minutes', 'server1', 'INFO', 52.1, 65.2, 251.0, 14.8, 8.9),
    (NOW() - INTERVAL '40 minutes', 'server1', 'INFO', 46.8, 62.8, 251.2, 15.5, 8.7),
    (NOW() - INTERVAL '1 hour', 'server2', 'INFO', 38.2, 55.1, 180.2, 12.5, 7.2),
    (NOW() - INTERVAL '55 minutes', 'server2', 'INFO', 40.5, 56.8, 180.3, 13.2, 7.8),
    (NOW() - INTERVAL '50 minutes', 'server2', 'ERROR', 92.5, 88.2, 180.5, 35.8, 22.5),
    (NOW() - INTERVAL '45 minutes', 'server2', 'WARN', 85.2, 82.5, 180.7, 28.5, 18.2),
    (NOW() - INTERVAL '40 minutes', 'server2', 'INFO', 42.8, 58.5, 180.9, 13.8, 7.5);

-- Add compression policy (compress data older than 7 days)
ALTER TABLE sensor_data SET (timescaledb.compress);
SELECT add_compression_policy('sensor_data', INTERVAL '7 days');

ALTER TABLE app_metrics SET (timescaledb.compress);
SELECT add_compression_policy('app_metrics', INTERVAL '3 days');

-- Add retention policy (drop data older than 90 days)
SELECT add_retention_policy('server_logs', INTERVAL '90 days');

-- ==============================================
-- Create indexes for common queries
-- ==============================================
CREATE INDEX ON sensor_data (sensor_id, time DESC);
CREATE INDEX ON app_metrics (service_name, endpoint, time DESC);
CREATE INDEX ON stock_prices (symbol, time DESC);
CREATE INDEX ON server_logs (hostname, time DESC);

-- ==============================================
-- Display summary
-- ==============================================
\echo 'TimescaleDB initialized successfully!'
\echo ''
\echo 'Hypertables created:'
\echo '  - sensor_data (IoT sensor readings)'
\echo '  - app_metrics (Application performance metrics)'
\echo '  - stock_prices (Stock market data with space partitioning)'
\echo '  - server_logs (Server monitoring logs)'
\echo ''
\echo 'Continuous aggregates:'
\echo '  - sensor_data_hourly (Hourly sensor averages)'
\echo '  - app_metrics_5min (5-minute performance summary)'
\echo '  - stock_prices_daily (Daily OHLCV data)'
\echo ''
\echo 'Policies configured:'
\echo '  - Compression: sensor_data (7 days), app_metrics (3 days)'
\echo '  - Retention: server_logs (90 days)'
\echo '  - Auto-refresh: All continuous aggregates'
