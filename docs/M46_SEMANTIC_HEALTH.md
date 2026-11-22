# M46 — Semantic warehouse health

The read-only warehouse health command now checks **data correctness**, not merely file existence, report success and model presence. After verifying Bronze integrity and required mart names, it invokes the existing eight-check DuckDB semantic quality gate.

The dedicated M46 workflow first builds a real, healthy synthetic warehouse, then intentionally corrupts the daily aggregate table. The expected result is an unhealthy status with a semantic-quality issue, despite all three warehouse models still existing.

This is a fail-closed offline regression test, not a production monitoring service. No live broker or operational database is modified.
