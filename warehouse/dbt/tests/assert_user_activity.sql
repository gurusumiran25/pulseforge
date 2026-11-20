-- One user has cross-midnight activity but only one session.
with actual as (
  select user_id, sessions, active_days, events
  from {{ ref('fct_user_activity') }}
), expected as (
  select 'user-a' as user_id, 1 as sessions, 2 as active_days, 4 as events
  union all
  select 'user-b', 1, 1, 1
  union all
  select 'user-c', 1, 1, 1
)
select * from (
  (select * from actual except select * from expected)
  union all
  (select * from expected except select * from actual)
)
