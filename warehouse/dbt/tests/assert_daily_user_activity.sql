-- Check the two dates of user-a's session independently.
with actual as (
  select cast(activity_date_utc as varchar) as activity_date, user_id, sessions, events
  from {{ ref('agg_daily_user_activity') }}
), expected as (
  select '2026-11-19' as activity_date, 'user-a' as user_id, 1 as sessions, 2 as events
  union all
  select '2026-11-20', 'user-a', 1, 2
  union all
  select '2026-11-20', 'user-b', 1, 1
  union all
  select '2026-11-20', 'user-c', 1, 1
)
select * from (
  (select * from actual except select * from expected)
  union all
  (select * from expected except select * from actual)
)
