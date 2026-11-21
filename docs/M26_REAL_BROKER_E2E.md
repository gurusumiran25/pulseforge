# M26 — Real broker-backed integration

This test aims to exercise the actual FastAPI batch endpoint, Kafka producer delivery, a real Redpanda broker, the consumer's Kafka poll/offset commit path, disposable SQLite storage, and Silver/Gold SQL views. The CI service starts a disposable Redpanda container; no local terminal or operational database is involved.

## Boundaries
- **Covered when CI passes:** HTTP request through FastAPI TestClient, real Kafka delivery and consumption, SQLite persistence, SQL analytics counts.
- **Not yet covered:** dbt transformation of the generated broker events, rendered Streamlit dashboard, restart/rebalance recovery, DLQ edge cases, production deployment.
- Each run creates unique topics and a unique consumer group to avoid cross-run contamination.
- A missing `M26_KAFKA_BOOTSTRAP` causes the test to skip in ordinary pytest; dedicated CI supplies it.
- This milestone is not verified until the dedicated M26 workflow succeeds.
