# PulseForge architecture (design baseline v0.1)

Synthetic journey generator -> FastAPI ingestion -> Kafka-compatible broker (Redpanda) -> raw landing store -> processing consumer -> analytical warehouse -> dbt models -> metrics API / Streamlit dashboard.

An observability service checks freshness, completeness, uniqueness, volume, consistency and anomalies. Airflow orchestration follows the first working vertical slice.

**Phase 0:** contracts and documentation only. **Phase 1:** local persistence before streaming.

The architecture is a plan, not a claim of implemented components.
