# M32 — SQLite-to-Bronze warehouse handoff

The Kafka consumer persists validated events in SQLite. M32 adds an **explicit, read-only export** of the committed SQLite event rows into a dbt-compatible Bronze CSV snapshot.

`python -m services.analytics.bronze_export --db-path <isolated-events.db> --output <bronze.csv>`

The export selects event IDs in stable order, writes five dbt source fields, and atomically replaces the output CSV only after successful completion. Duplicate event IDs are already prevented by SQLite's primary key.

This is a **batch snapshot**, not a continuously running Kafka-to-DuckDB connector. The existing M27/M28 workflows verify dbt and dashboard parity using a generated CSV. A later integration can invoke this export against the M26 broker-consumer SQLite database and run dbt against the result.

**Safety:** Never point the output at an operational database or overwrite existing data without review. This tool does not mutate the SQLite source. Use disposable databases for tests and demonstrations.
