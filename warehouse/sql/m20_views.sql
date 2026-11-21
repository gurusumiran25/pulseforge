-- M20.1: read-only warehouse views over the existing SQLite events table.
-- No writes to events and no destructive migrations.
-- Grain: silver_events = one stored event_id; gold_session_funnel = one session_id.
-- SQLite JSON1 support required.
CREATE VIEW IF NOT EXISTS silver_events AS
SELECT
  event_id,
  event_name,
  user_id,
  session_id,
  event_time,
  ingested_at,
  json_extract(payload, '$.schema_version') AS schema_version,
  json_extract(payload, '$.source') AS source,
  json_extract(payload, '$.platform') AS platform,
  json_extract(payload, '$.properties.product_id') AS product_id,
  json_extract(payload, '$.properties.order_id') AS order_id,
  CAST(json_extract(payload, '$.properties.amount') AS REAL) AS payment_amount,
  json_extract(payload, '$.properties.currency') AS currency
FROM events
WHERE json_valid(payload) = 1;

CREATE VIEW IF NOT EXISTS gold_session_funnel AS
SELECT
  session_id,
  MIN(event_time) AS first_event_time,
  MAX(event_time) AS last_event_time,
  COUNT(*) AS event_count,
  MAX(CASE WHEN event_name = 'product_viewed' THEN 1 ELSE 0 END) AS viewed_product,
  MAX(CASE WHEN event_name = 'add_to_cart' THEN 1 ELSE 0 END) AS added_to_cart,
  MAX(CASE WHEN event_name = 'checkout_started' THEN 1 ELSE 0 END) AS started_checkout,
  MAX(CASE WHEN event_name = 'payment_succeeded' THEN 1 ELSE 0 END) AS completed_payment
FROM silver_events
GROUP BY session_id;

CREATE VIEW IF NOT EXISTS gold_daily_funnel AS
SELECT
  substr(first_event_time, 1, 10) AS cohort_date_utc,
  COUNT(*) AS sessions,
  SUM(viewed_product) AS sessions_with_product_view,
  SUM(added_to_cart) AS sessions_with_cart,
  SUM(started_checkout) AS sessions_with_checkout,
  SUM(completed_payment) AS sessions_with_payment
FROM gold_session_funnel
GROUP BY substr(first_event_time, 1, 10);
