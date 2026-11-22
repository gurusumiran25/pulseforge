# M43 — Enforced warehouse data quality

The one-shot SQLite -> Bronze -> dbt DuckDB batch now executes M42 semantic quality checks after dbt finishes. If any of the eight checks fails, the batch raises an error instead of returning success. M39 reporting therefore records the failure, and M40 retries do not retry this non-transient validation error.

A dedicated GitHub Actions workflow installs dbt-duckdb and exercises the **real** batch, without mocking dbt or the quality checker. Other unit tests mock dbt and quality independently.

Limitations: this verifies internal consistency and does not prove correctness against external production data, transactional writes, freshness SLAs, or operational availability.
