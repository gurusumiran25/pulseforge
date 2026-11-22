# M40 — Bounded isolated warehouse retries

M40 wraps the M39 reported batch execution with at most five attempts. Each attempt gets its own fresh workspace and JSON report; previous attempt data is never overwritten. Only dbt subprocess failures and timeouts are retried. Input validation, missing source, manifest integrity failures, and workspace safety errors stop immediately.

Usage: `python -m services.analytics.warehouse_retry --db-path <events.db> --output-root <new-empty-directory> --max-attempts 3 --delay-seconds 2`

The output root must be empty, and must not contain the source SQLite database. There is no automatic cleanup: failed attempts and reports are retained for inspection.

**Limitations:** Retries are synchronous and manual-invocation only; no jitter, distributed coordination, process crash recovery, or scheduler. A deterministic dbt error may repeat, so retries are bounded and limited to dbt subprocess errors. CI tests mock the reporting wrapper to isolate retry policy.
