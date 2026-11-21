-- Fails when the known synthetic fixture violates the agreed session-start cohort.
with actual as (
  select
    cast(cohort_date_utc as varchar) as cohort_date,
    sessions,
    sessions_with_product_view,
    sessions_with_payment
  from {{ ref('agg_daily_funnel') }}
), expected as (
  select '2026-11-19' as cohort_date, 1 as sessions, 1 as sessions_with_product_view, 1 as sessions_with_payment
  union all
  select '2026-11-20', 2, 1, 0
)
select * from (
  (select * from actual except select * from expected)
  union all
  (select * from expected except select * from actual)
)
