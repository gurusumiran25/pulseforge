# M33 — Real broker through dbt DuckDB warehouse

Dedicated CI spins up a disposable Redpanda container, creates unique topics, publishes ten generated customer journeys via FastAPI batch ingestion, polls real Kafka consumer messages, and persists validated events to an isolated SQLite database.

The test runs SQLite Silver/Gold views, exports committed rows through the M32 atomic Bronze snapshot exporter, builds dbt DuckDB models, and checks total events, sessions, paid sessions and UTC daily cohorts against the SQLite baseline.

This is a **single test connecting the real broker network to dbt warehouse marts**. It is not continuous Kafka-to-DuckDB streaming: the handoff is an explicitly invoked batch snapshot. It does not test a deployed Streamlit browser, production load, or long-running orchestration.
