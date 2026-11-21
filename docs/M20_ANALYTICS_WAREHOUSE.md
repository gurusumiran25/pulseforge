# M20 — Analytics Warehouse, SQL Transformations & dbt

## M20.1: Warehouse contract (implemented)

The source-of-truth Bronze layer remains the existing `events` table in SQLite; no production data is migrated or overwritten. `warehouse/sql/m20_views.sql` defines three **read-only** SQLite views:

- `silver_events`: one record per stored `event_id`, with commonly queried attributes extracted from the validated JSON envelope.
- `gold_session_funnel`: one record per `session_id`, with binary flags for product view, add-to-cart, checkout, and successful payment.
- `gold_daily_funnel`: sessions grouped by UTC date of their **first event**; the date is a session-start cohort, not necessarily the event's payment date.

These are exploratory warehouse contracts, **not** a deployed warehouse or completed dbt pipeline. Funnel flags are independent observations, not evidence that the steps happened in chronological order. `gold_daily_funnel` therefore reports stage participation, not a strictly ordered conversion funnel.

## M20 implementation sequence

1. **M20.1**: establish Bronze/Silver/Gold contracts and safe SQL views.
2. **M20.2**: create reproducible synthetic-data warehouse verification and SQL quality tests.
3. **M20.3**: introduce a dbt project, explicit source declarations, staging and dimensional models, and tests; choose a supported adapter and document local installation.
4. **M20.4**: validate funnels, conversion, cohorts and retention with clear metric definitions and edge cases.
5. **M20.5**: integrate CI and document lineage, limitations, and evidence.

## Safety and limitations

- Do not run SQL against `data/automation/*.db` or the operational monitoring database.
- Apply these views only to a **disposable copy** of the event database or a synthetic test fixture until verification is complete.
- SQLite must provide JSON1 functions.
- Existing `INSERT OR IGNORE` event-ID conflict semantics remain unchanged and are tracked for later hardening.
- Timestamp strings are generated as UTC ISO-8601 by the event contract, but historical data quality must still be checked.
- No changes are made to streaming, Windows Task Scheduler, existing event storage, or `main`.

## M20.2: Synthetic warehouse verification (implemented; CI verified at 743928f)

`tests/warehouse/test_m20_warehouse_views.py` uses pytest's `tmp_path` fixture to create a disposable SQLite event store, loads the exact `warehouse/sql/m20_views.sql` definitions, and validates:

1. Silver-layer JSON extraction and row count.
2. Gold session grain and independently observed funnel flags.
3. UTC session-start cohort aggregation across midnight.
4. Duplicate `event_id` suppression in warehouse metrics.
5. Empty warehouse behavior.
6. Purchase-stage participation without preceding steps (not a chronological funnel).

The standard `.github/workflows/tests.yml` runs `python -m pytest` on pushes and pull requests, so these tests are included automatically. **Both standard pytest and dbt workflows passed at commit 743928f. Subsequent M20.4 assertions require a fresh CI run.**

Run locally without Docker:
```powershell
python -m pytest -v tests/warehouse/test_m20_warehouse_views.py
```

This suite does not mutate any operational database or create persistent test files in the repository.

## M20.3: Isolated dbt warehouse (implemented)

The `warehouse/dbt` project uses `dbt-duckdb`, an **in-memory** DuckDB profile, and a synthetic Bronze seed. It declares a Bronze source, a staging model, session and daily funnel marts, user activity marts, and schema tests. `.github/workflows/m20-dbt.yml` executes `dbt seed` followed by `dbt build` on changes to this project. This is a portable demonstration pipeline, not a connection to production event storage.

## M20.4: Metric semantics and exact-value verification (implemented; CI pending)

Four dbt singular tests verify the known synthetic fixture exactly: session-stage participation, session-start daily cohorts, per-user activity, and per-day user activity. These tests detect incorrect metric results that generic not-null and uniqueness tests would miss.

- **Session participation**: `completed_payment` means at least one successful payment event in the session. It is not an ordered checkout conversion.
- **Session-start cohort date**: `agg_daily_funnel` assigns the entire session to its first observed event's UTC date.
- **Active days**: `fct_user_activity.active_days` counts distinct UTC dates with events. It is not D1/D7 retention.
- **Daily user activity**: `agg_daily_user_activity` has one row per (UTC activity date, user). One cross-midnight session can contribute to two dates.
- **Known limitation**: Synthetic seed models only a normalized subset of event fields; it does not validate full raw JSON-to-dbt ingestion or genuine production retention.

## M20.5: CI and lineage

The standard Python tests and the separate dbt workflow both reported successful completion for commit `743928f`. The four new singular assertions were added later and must pass their own CI run before the pull request is considered verified. Data lineage is: synthetic Bronze CSV → `stg_events` → session/user activity marts → daily marts. No operational database is accessed.
