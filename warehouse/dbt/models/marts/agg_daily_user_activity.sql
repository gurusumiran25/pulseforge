-- Activity date is the event's UTC date, not the user's first-seen date.
-- Grain: (activity_date_utc, user_id); this is a retention input, not a cohort rate.
select
    cast(event_time as date) as activity_date_utc,
    user_id,
    count(distinct session_id) as sessions,
    count(*) as events
from {{ ref('stg_events') }}
group by 1, 2
