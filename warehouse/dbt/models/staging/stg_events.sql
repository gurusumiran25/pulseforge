select
    cast(event_id as varchar) as event_id,
    cast(event_name as varchar) as event_name,
    cast(session_id as varchar) as session_id,
    cast(user_id as varchar) as user_id,
    cast(event_time as timestamp) as event_time
from {{ source('bronze', 'bronze_events') }}
