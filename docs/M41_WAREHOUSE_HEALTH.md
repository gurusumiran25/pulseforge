# M41 — Offline warehouse health checks

M41 adds a read-only command to inspect a completed M39 batch report, verify its M37 Bronze manifest and event count, confirm the DuckDB file exists, and inspect required dbt model names.

`python -m services.analytics.warehouse_health --report <successful-run-report.json>`

The command emits JSON with `healthy` and `issues` fields and exits nonzero when unhealthy. It never creates or repairs a database. The check is offline and on-demand, not a continuously running monitor, alerting service or scheduler. It validates model presence rather than full data-quality semantics or production SLA compliance.

The DuckDB Python package is needed to inspect marts. If unavailable, the check reports an issue instead of silently passing.
