# M86 — Curated BI publication contract

Status: implementation design; not yet a deployed feed or native Power BI report.

## Inputs and grain
- stg_events: one event_id, UTC event_time, event_name, session_id, user_id.
- fct_session_funnel: one session, observed stage flags (not ordered transitions).
- agg_daily_user_activity: one UTC activity date and synthetic user.
- Payment sidecar: one successful payment or refund event, join to staging by event_id. Failed payment counts come from staging. Never sum across currencies.
- Product attribution requires a separate allowlisted projection of validated synthetic product-view payloads from SQLite; the existing Bronze schema cannot supply product IDs.

## Publication
Build exports from the same isolated SQLite/dbt batch after existing quality and parity gates. Use a dedicated BI output directory, never replace the Streamlit artifacts. Write CSV files with explicit schemas into a temporary directory, validate unique keys, foreign keys, counts and monetary reconciliation, then publish an immutable content-addressed snapshot directory. Atomically replace a small current.json pointer only after all files and manifest hashes are verified. Consumers must pin one snapshot per refresh; independent Power Query evaluations of a mutable pointer do not guarantee snapshot consistency. A refresh orchestrator or explicit immutable snapshot parameter is required for strict consistency.

## Initial tables
| Table | Grain |
|---|---|
| FactSession | session_id |
| FactEvent | event_id |
| FactPayment | payment/refund event_id |
| FactDailyUser | UTC date and synthetic user |
| DimDate | UTC date |
| DimCustomer | synthetic user |
| DimCurrency | currency code |
| FactProductView (later) | product-view event_id |

No full payloads, search text, credentials or real customer information. Reject non-synthetic user identifiers in the public export. Preserve UTC semantics and currency separation.

## Acceptance
Test deterministic schemas, hash verification, orphan and duplicate rejection, failure preserving the previous pointer, concurrent publication safety, dashboard/dbt parity, and successful/failed/refunded payment semantics. Schedule integration and Power BI Desktop/Service validation are separate gates. No claim of PBIX, PBIP rendering or Service refresh until verified.
