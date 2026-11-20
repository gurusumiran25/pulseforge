select
    session_id,
    min(event_time) as first_event_time,
    max(event_time) as last_event_time,
    count(*) as event_count,
    max(case when event_name = 'product_viewed' then 1 else 0 end) as viewed_product,
    max(case when event_name = 'add_to_cart' then 1 else 0 end) as added_to_cart,
    max(case when event_name = 'checkout_started' then 1 else 0 end) as started_checkout,
    max(case when event_name = 'payment_succeeded' then 1 else 0 end) as completed_payment
from {{ ref('stg_events') }}
group by session_id
