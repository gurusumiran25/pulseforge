select
    cast(first_event_time as date) as cohort_date_utc,
    count(*) as sessions,
    sum(viewed_product) as sessions_with_product_view,
    sum(added_to_cart) as sessions_with_cart,
    sum(started_checkout) as sessions_with_checkout,
    sum(completed_payment) as sessions_with_payment
from {{ ref('fct_session_funnel') }}
group by 1
