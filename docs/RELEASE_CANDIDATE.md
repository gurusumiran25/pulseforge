# PulseForge portfolio release candidate — acceptance record

This is a **release-candidate checklist**, not a claim that a tagged release has already shipped.

## Demonstrable capabilities

- Versioned Pydantic event validation and synthetic customer journeys
- FastAPI ingestion, Kafka-compatible producer and consumer, SQLite event-ID deduplication
- Real Redpanda integration in isolated GitHub Actions workflows
- Atomic Bronze CSV export and SHA-256/row-count manifest verification
- Real dbt DuckDB staging, session and daily marts
- Eight semantic data-quality checks, fail-closed warehouse batch, offline health check
- One-command synthetic demonstration with dashboard/warehouse metric parity
- Streamlit dashboard and AppTest rendering checks
- Isolated batch run reports and bounded retry attempts

## Run the synthetic demonstration

With Python 3.12 and an empty output directory:

```bash
python -m pip install -e '.[dev,portfolio]'
python -m services.analytics.portfolio_demo --output-root ./pulseforge-demo --sessions 20
```

Inspect `pulseforge-demo/demo-summary.json` and `pulseforge-demo/run-report.json`. The generated directory is ignored by Git.

## Acceptance requirements

Before tagging a release, verify the [release checklist](RELEASE_CHECKLIST.md) against a single final commit SHA. Check every required workflow including real broker, real dbt, Streamlit and corruption regression. Record the actual test results, not assumptions.

## Known limitations

- Synthetic data only; no customer data or deployed users
- One-shot local warehouse batch, not continuously scheduled Kafka-to-warehouse ingestion
- Dashboard reads a configurable Bronze CSV, not DuckDB directly
- Local SQLite and DuckDB, not horizontally scaled storage
- Dependency ranges are not an immutable lockfile
- No production secrets management, SLOs, cloud infrastructure or 24/7 observability
- Bounded retry policy is not a distributed recovery controller
- Browser-based visual review and sustained load benchmarks remain separate validation tasks

## Release wording

A successful portfolio release demonstrates a reproducible, independently tested local analytics pipeline. It **does not** establish production availability, enterprise scale, or real-world business impact.
