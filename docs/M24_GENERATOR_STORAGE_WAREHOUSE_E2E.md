# M24 — Generator-to-warehouse integration verification

## Verified scope (pending CI)
The test suite exercises real `generate_customer_journey` events, validated Pydantic envelopes, the real SQLite bulk insert path, the exact M20 SQL Silver/Gold views, session-level metrics, UTC session-start cohort aggregation, and replay idempotency.

Forty generated journeys use fixed random seeds, while event IDs and UTC timestamps remain dynamic. The test computes independent expected values from the generated journeys, so it does not depend on fixed absolute dates or generated UUIDs.

## Safety
All data is stored under pytest's disposable `tmp_path`. The operational `data/storage/pulseforge.db` and any `data/automation` databases are never accessed.

## Explicit gaps
This is **not yet** a complete generator → Kafka → FastAPI → SQLite → dbt → Streamlit end-to-end test. It tests the generator → SQLite → SQL views segment only. Kafka/Redpanda, API ingestion, dbt transformation against generated events, and actual Streamlit rendering need further independent coverage. The existing `INSERT OR IGNORE` semantics do not detect conflicting payloads with an existing event ID.
