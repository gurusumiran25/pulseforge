# M61: Retention dashboard data boundary

The Streamlit dashboard now shows observed D1/D7/D14/D30 exact-day user
activity retention, using user IDs and UTC timestamps from the verified
Bronze CSV. These metrics are descriptive and use the earliest observed
activity **within the selected session cohort window**; they are not
verified acquisition cohorts. The most recent cohorts are right-censored
because future follow-up days have not occurred. A zero in those columns
must not be interpreted as churn.

RFM, refund-adjusted customer value, and A/B experiment analysis are
implemented as tested backend modules, **not** dashboard metrics yet.
The current public Bronze export contains only event_id, event_name,
session_id, user_id, and event_time. It does not contain order amounts,
currencies, refund records, or randomized experiment assignments.
Do not fabricate these fields or infer revenue from event counts.
A future versioned, synthetic-safe enrichment schema and quality tests
are prerequisites to exposing those modules in the dashboard.
