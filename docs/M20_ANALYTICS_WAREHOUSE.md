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

## M20.2: Synthetic warehouse verification (implemented; CI pending)

`tests/warehouse/test_m20_warehouse_views.py` uses pytest's `tmp_path` fixture to create a disposable SQLite event store, loads the exact `warehouse/sql/m20_views.sql` definitions, and validates:

1. Silver-layer JSON extraction and row count.
2. Gold session grain and independently observed funnel flags.
3. UTC session-start cohort aggregation across midnight.
4. Duplicate `event_id` suppression in warehouse metrics.
5. Empty warehouse behavior.
6. Purchase-stage participation without preceding steps (not a chronological funnel).

The standard `.github/workflows/tests.yml` runs `python -m pytest` on pushes and pull requests, so these tests are included automatically. **A successful M20.2 run is not yet confirmed.**

Run locally without Docker:
```powershell
python -m pytest -v tests/warehouse/test_m20_warehouse_views.py
```

This suite does not mutate any operational database or create persistent test files in the repository.
