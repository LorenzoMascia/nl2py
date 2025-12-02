-- ClickHouse Initialization Script for NL2Py
-- This script creates sample databases, tables, and data for testing

-- Create analytics database
CREATE DATABASE IF NOT EXISTS analytics;

-- Switch to analytics database
USE analytics;

-- Create events table for web analytics
CREATE TABLE IF NOT EXISTS events (
    event_date Date,
    event_time DateTime,
    user_id UInt32,
    session_id String,
    event_type LowCardinality(String),
    page_url String,
    referrer String,
    country LowCardinality(String),
    city String,
    device_type Enum8('desktop' = 1, 'mobile' = 2, 'tablet' = 3),
    browser LowCardinality(String),
    duration_sec UInt32
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, user_id, event_time);

-- Insert sample events data
INSERT INTO events VALUES
    ('2025-01-14', '2025-01-14 10:15:00', 1001, 'sess_abc123', 'pageview', '/home', 'https://google.com', 'US', 'New York', 'desktop', 'Chrome', 45),
    ('2025-01-14', '2025-01-14 10:20:00', 1001, 'sess_abc123', 'click', '/products', '/home', 'US', 'New York', 'desktop', 'Chrome', 120),
    ('2025-01-14', '2025-01-14 10:30:00', 1002, 'sess_def456', 'pageview', '/home', 'https://facebook.com', 'UK', 'London', 'mobile', 'Safari', 30),
    ('2025-01-14', '2025-01-14 10:35:00', 1002, 'sess_def456', 'pageview', '/about', '/home', 'UK', 'London', 'mobile', 'Safari', 60),
    ('2025-01-14', '2025-01-14 11:00:00', 1003, 'sess_ghi789', 'pageview', '/products', 'https://twitter.com', 'DE', 'Berlin', 'desktop', 'Firefox', 90),
    ('2025-01-14', '2025-01-14 11:15:00', 1004, 'sess_jkl012', 'pageview', '/home', 'direct', 'FR', 'Paris', 'tablet', 'Safari', 25),
    ('2025-01-14', '2025-01-14 11:30:00', 1005, 'sess_mno345', 'click', '/checkout', '/products', 'US', 'San Francisco', 'desktop', 'Chrome', 180),
    ('2025-01-14', '2025-01-14 12:00:00', 1003, 'sess_ghi789', 'purchase', '/checkout', '/products', 'DE', 'Berlin', 'desktop', 'Firefox', 240);

-- Create metrics table for time-series data
CREATE TABLE IF NOT EXISTS metrics (
    timestamp DateTime,
    metric_name LowCardinality(String),
    value Float64,
    tags Map(String, String),
    host LowCardinality(String)
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (metric_name, timestamp);

-- Insert sample metrics
INSERT INTO metrics VALUES
    ('2025-01-14 10:00:00', 'cpu_usage', 45.2, {'env': 'prod', 'region': 'us-east-1'}, 'server-01'),
    ('2025-01-14 10:00:00', 'memory_usage', 67.8, {'env': 'prod', 'region': 'us-east-1'}, 'server-01'),
    ('2025-01-14 10:00:00', 'cpu_usage', 52.1, {'env': 'prod', 'region': 'us-west-2'}, 'server-02'),
    ('2025-01-14 10:05:00', 'cpu_usage', 48.7, {'env': 'prod', 'region': 'us-east-1'}, 'server-01'),
    ('2025-01-14 10:05:00', 'memory_usage', 69.2, {'env': 'prod', 'region': 'us-east-1'}, 'server-01'),
    ('2025-01-14 10:10:00', 'cpu_usage', 51.3, {'env': 'prod', 'region': 'us-east-1'}, 'server-01'),
    ('2025-01-14 10:10:00', 'disk_io', 1250.5, {'env': 'prod', 'region': 'us-east-1'}, 'server-01');

-- Create sales table
CREATE TABLE IF NOT EXISTS sales (
    sale_date Date,
    sale_time DateTime,
    order_id UInt64,
    customer_id UInt32,
    product_id UInt32,
    quantity UInt16,
    price Decimal(10, 2),
    total Decimal(10, 2),
    country LowCardinality(String),
    payment_method LowCardinality(String)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(sale_date)
ORDER BY (sale_date, order_id);

-- Insert sample sales
INSERT INTO sales VALUES
    ('2025-01-14', '2025-01-14 09:15:00', 10001, 1001, 501, 2, 29.99, 59.98, 'US', 'credit_card'),
    ('2025-01-14', '2025-01-14 09:30:00', 10002, 1002, 502, 1, 149.99, 149.99, 'UK', 'paypal'),
    ('2025-01-14', '2025-01-14 10:00:00', 10003, 1003, 503, 3, 19.99, 59.97, 'DE', 'credit_card'),
    ('2025-01-14', '2025-01-14 10:45:00', 10004, 1004, 501, 1, 29.99, 29.99, 'FR', 'debit_card'),
    ('2025-01-14', '2025-01-14 11:20:00', 10005, 1005, 504, 2, 99.99, 199.98, 'US', 'credit_card'),
    ('2025-01-14', '2025-01-14 12:00:00', 10006, 1006, 502, 1, 149.99, 149.99, 'CA', 'paypal'),
    ('2025-01-14', '2025-01-14 12:30:00', 10007, 1003, 505, 5, 9.99, 49.95, 'DE', 'credit_card');

-- Create materialized view for daily sales aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_sales_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(sale_date)
ORDER BY (sale_date, country, payment_method)
AS SELECT
    sale_date,
    country,
    payment_method,
    count() as order_count,
    sum(quantity) as total_quantity,
    sum(total) as total_revenue
FROM sales
GROUP BY sale_date, country, payment_method;

-- Create materialized view for hourly event stats
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_events_mv
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, event_hour, country, event_type)
AS SELECT
    event_date,
    toHour(event_time) as event_hour,
    country,
    event_type,
    count() as event_count,
    count(DISTINCT user_id) as unique_users,
    count(DISTINCT session_id) as unique_sessions,
    avg(duration_sec) as avg_duration
FROM events
GROUP BY event_date, event_hour, country, event_type;

-- Create logs table for log aggregation
CREATE TABLE IF NOT EXISTS logs (
    timestamp DateTime64(3),
    log_level Enum8('DEBUG' = 1, 'INFO' = 2, 'WARNING' = 3, 'ERROR' = 4, 'CRITICAL' = 5),
    service LowCardinality(String),
    host LowCardinality(String),
    message String,
    trace_id String,
    user_id Nullable(UInt32),
    duration_ms Nullable(UInt32),
    status_code Nullable(UInt16),
    error_type LowCardinality(Nullable(String))
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(timestamp)
ORDER BY (timestamp, service, log_level)
TTL timestamp + INTERVAL 30 DAY;  -- Auto-delete logs older than 30 days

-- Insert sample logs
INSERT INTO logs VALUES
    ('2025-01-14 10:00:00.123', 'INFO', 'api-gateway', 'server-01', 'Request received', 'trace-abc-123', 1001, 45, 200, NULL),
    ('2025-01-14 10:00:00.456', 'INFO', 'auth-service', 'server-02', 'User authenticated', 'trace-abc-123', 1001, 120, 200, NULL),
    ('2025-01-14 10:00:01.789', 'ERROR', 'payment-service', 'server-03', 'Payment processing failed', 'trace-def-456', 1002, 2500, 500, 'PaymentError'),
    ('2025-01-14 10:00:02.012', 'WARNING', 'api-gateway', 'server-01', 'High latency detected', 'trace-ghi-789', 1003, 3200, 200, NULL),
    ('2025-01-14 10:00:03.345', 'INFO', 'notification-service', 'server-04', 'Email sent', 'trace-jkl-012', 1004, 890, 200, NULL);

-- Create example distributed table (for cluster setups)
-- Note: This is for reference only, single-node setup doesn't use distributed tables
-- CREATE TABLE IF NOT EXISTS events_distributed AS events
-- ENGINE = Distributed(cluster_name, analytics, events, rand());

-- Show created tables
SHOW TABLES FROM analytics;

-- Display sample query results
SELECT 'Sample Events by Country:' as info;
SELECT country, count() as events, count(DISTINCT user_id) as users
FROM events
GROUP BY country
ORDER BY events DESC;

SELECT 'Sample Sales by Country:' as info;
SELECT country, sum(total) as revenue, count() as orders
FROM sales
GROUP BY country
ORDER BY revenue DESC;

SELECT 'Hourly Event Statistics (from materialized view):' as info;
SELECT event_date, event_hour, sum(event_count) as total_events, sum(unique_users) as users
FROM hourly_events_mv
GROUP BY event_date, event_hour
ORDER BY event_date, event_hour;
