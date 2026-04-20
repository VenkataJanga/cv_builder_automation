-- Audit query pack for transaction_event_logs
-- Usage (MySQL): SOURCE scripts/audit_queries.sql;

-- 1) Latest login attempts (success and failed)
SELECT
    id,
    created_at,
    actor_username,
    module_name,
    operation,
    status,
    http_status,
    event_message
FROM transaction_event_logs
WHERE module_name = 'auth'
  AND operation = 'login'
ORDER BY created_at DESC, id DESC
LIMIT 200;

-- 2) Failed logins in the last 24 hours
SELECT
    created_at,
    actor_username,
    http_status,
    event_message,
    payload
FROM transaction_event_logs
WHERE module_name = 'auth'
  AND operation = 'login'
  AND status = 'failed'
  AND created_at >= (UTC_TIMESTAMP() - INTERVAL 24 HOUR)
ORDER BY created_at DESC;

-- 3) Activity summary by user over the last 7 days
SELECT
    COALESCE(actor_username, 'unknown') AS actor_username,
    COUNT(*) AS total_events,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_count,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_count,
    MIN(created_at) AS first_seen,
    MAX(created_at) AS last_seen
FROM transaction_event_logs
WHERE created_at >= (UTC_TIMESTAMP() - INTERVAL 7 DAY)
GROUP BY COALESCE(actor_username, 'unknown')
ORDER BY total_events DESC;

-- 4) What actions were performed per module in the last 24 hours
SELECT
    module_name,
    operation,
    status,
    COUNT(*) AS events
FROM transaction_event_logs
WHERE created_at >= (UTC_TIMESTAMP() - INTERVAL 24 HOUR)
GROUP BY module_name, operation, status
ORDER BY module_name, operation, status;

-- 5) Full timeline for a specific actor (set @actor before running)
SET @actor = 'admin';
SELECT
    id,
    created_at,
    actor_user_id,
    actor_username,
    module_name,
    operation,
    status,
    http_status,
    source_channel,
    event_message,
    payload
FROM transaction_event_logs
WHERE actor_username = @actor
ORDER BY created_at DESC, id DESC
LIMIT 500;

-- 6) Full timeline for a specific session (set @session_id before running)
SET @session_id = 'replace-with-session-id';
SELECT
    id,
    created_at,
    actor_username,
    module_name,
    operation,
    status,
    http_status,
    source_channel,
    event_message,
    payload
FROM transaction_event_logs
WHERE session_id = @session_id
ORDER BY created_at ASC, id ASC;

-- 7) Error trend by hour over the last 48 hours
SELECT
    DATE_FORMAT(created_at, '%Y-%m-%d %H:00:00') AS hour_bucket,
    COUNT(*) AS failed_events
FROM transaction_event_logs
WHERE status = 'failed'
  AND created_at >= (UTC_TIMESTAMP() - INTERVAL 48 HOUR)
GROUP BY DATE_FORMAT(created_at, '%Y-%m-%d %H:00:00')
ORDER BY hour_bucket ASC;

-- 8) Top error messages in the last 7 days
SELECT
    COALESCE(NULLIF(error_message, ''), 'no_error_message') AS error_message,
    COUNT(*) AS occurrences
FROM transaction_event_logs
WHERE status = 'failed'
  AND created_at >= (UTC_TIMESTAMP() - INTERVAL 7 DAY)
GROUP BY COALESCE(NULLIF(error_message, ''), 'no_error_message')
ORDER BY occurrences DESC
LIMIT 50;
