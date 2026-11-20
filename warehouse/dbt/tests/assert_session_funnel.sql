-- Fails on missing/extra sessions or incorrect stage participation.
with actual as (
  select session_id, event_count, viewed_product, added_to_cart, started_checkout, completed_payment
  from {{ ref('fct_session_funnel') }}
), expected as (
  select 'session-a' as session_id, 4 as event_count, 1 as viewed_product, 1 as added_to_cart, 1 as started_checkout, 1 as completed_payment
  union all
  select 'session-b', 1, 1, 0, 0, 0
  union all
  select 'session-c', 1, 0, 0, 0, 0
)
select * from (
  (select * from actual except select * from expected)
  union all
  (select * from expected except select * from actual)
)
