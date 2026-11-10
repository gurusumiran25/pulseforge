# PulseForge

**Product Intelligence & Data Reliability Platform** — a portfolio-grade synthetic e-commerce event analytics platform.

## Status
Phase 0: foundation. No streaming, warehouse, dashboard, or performance claims yet.

## MVP roadmap
1. Synthetic event generator and FastAPI ingestion endpoint with local persistence.
2. Redpanda event streaming, consumer, retries and dead-letter path.
3. Bronze/Silver/Gold warehouse and dbt models.
4. Funnel, retention, revenue, cohort and experiment metrics.
5. Data quality, anomalies, replay and run history.
6. Streamlit dashboard, Docker and CI.

## Local setup
Requires Python 3.10+.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```

## Event contract
See `contracts/events/event_envelope_v1.json` and `docs/event_catalogue.md`.

## Scope and privacy
Only synthetic pseudonymous data; no real customer data or secrets.

## Documentation
See `docs/architecture.md` and `docs/decisions/0001-local-first.md`.
