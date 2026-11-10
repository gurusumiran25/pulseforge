# ADR-0001: Local-first vertical slice

- Status: Accepted for initial implementation
- Context: The v0.1 report explicitly prioritizes a reproducible vertical slice over installing the full stack.
- Decision: Build a Python generator, FastAPI validation endpoint, local accepted/rejected persistence and tests before adding Redpanda, dbt, Airflow or BigQuery.
- Consequences: Faster local iteration and simpler debugging; later broker and warehouse adapters must preserve the event contract.
