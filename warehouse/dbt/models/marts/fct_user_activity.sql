-- One row per user. This is observed activity, not a full retention cohort.
select
    user_id,
    min(cast(event_time as date)) as first_active_date_utc,
    max(cast(event_time as date)) as last_active_date_utc,
    count(distinct session_id) as sessions,
    count(distinct cast(event_time as date)) as active_days,
    count(*) as events
from {{ ref('stg_events') }}
group by user_id
