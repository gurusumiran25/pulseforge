# M42 — DuckDB warehouse semantic quality gates

M42 introduces read-only quality checks for the existing dbt DuckDB models: unique event IDs, required fields, unique sessions, valid session flags, session event-count reconciliation, daily session-count reconciliation, daily metric bounds and exact daily mart parity with session aggregates.

Run: `python -m services.analytics.warehouse_quality --warehouse <warehouse.duckdb>`

The command emits machine-readable JSON and exits nonzero when any check fails. It never repairs or mutates the warehouse. A missing database is rejected rather than created. Checks validate internal model consistency, not external business truth or real-time freshness. M42 does not yet integrate the gate into warehouse batch orchestration.
