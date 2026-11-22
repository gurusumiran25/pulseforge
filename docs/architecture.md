# PulseForge architecture â€” implemented modules and planned extensions

**Status:** Local-first engineering portfolio. This document distinguishes implemented source modules from future infrastructure. A green pytest workflow does not certify a live Kafka broker or production deployment.

## 1. Event streaming path

```text
Synthetic generator or API client
          |
          v
Pydantic EventEnvelope validation (contracts/event_validation.py)
          |
          v
FastAPI ingestion (services/ingestion/main.py)
          |
          v
Kafka-compatible producer (services/streaming/producer.py)
          |
          v
Redpanda broker (configured in docker-compose.yml)
          |
          v
Consumer (services/streaming/consumer.py)
       /       \
      v         v
SQLite       Dead-letter topic for invalid payloads
storage      (only after confirmed delivery)
      |
      v
Funnel / revenue analytics and quality checks
```

- Producer delivery is confirmed before ingestion returns success.
- Batch ingestion is sequential and **not atomic**. A failure can occur after partial publication; retries can duplicate broker messages.
- The consumer commits offsets after confirmed SQLite handling or confirmed dead-letter publication.
- SQLite event IDs provide duplicate prevention at the storage layer.
- Live broker integration requires isolated topics and explicit approval; it is not part of standard pytest CI.

## 2. Daily simulation and reliability path

```text
Daily CLI (services/simulation/daily_cli.py)
          |
          v
Execution lock and atomic customer selection
          |
          v
Session planning and persona journeys
          |
          v
SQLite simulation/customer records + event storage + run ledger
          |
          v
Run identity / consistency verification
          |
          v
Quality reports, monitoring metrics, snapshots and alerts
          |
          v
Preview-only recovery policy evaluation
```

- Daily simulation can write operational data; `--dry-run` reports configuration without running the simulation.
- `AtomicDailySelector` reserves SQLite transactions and preserves same-day selections when configuration and seed match.
- Execution locking has Windows and POSIX implementations.
- Monitoring reads operational source databases and supports snapshot storage in separate modules.
- Self-healing planning is fail-closed. Automatic production recovery and scheduler activation are **not enabled**.

## 3. Analytics and data quality

- `services/analytics/funnel.py`: ordered, session-level funnel stage counts, conversion rates, and drop-off.
- `services/analytics/revenue.py`: payment and refund reconciliation, duplicate successful-order detection, per-currency revenue summaries.
- `services/quality/`: event scanning, integrity checks, quality scoring, and volume anomalies.
- `services/monitoring/`: read-only metric collection, alert generation, snapshot storage, monitoring API, and controlled recovery components.

## 4. Storage and path boundaries

The repository has multiple local SQLite contexts. In particular, the daily CLI defaults to `data/storage/` while monitoring modules often default to `data/automation/`. They must **not** be assumed to refer to the same database. Verify each command's configured paths before running it; never run write operations against existing operational data without authorization.

## 5. Test boundaries

`.github/workflows/tests.yml` installs development dependencies and runs pytest on Ubuntu / Python 3.12. The workflow validates its test suite, not a running Redpanda cluster, Windows Task Scheduler, or a continuously deployed monitoring service.

## 6. Implemented warehouse and dashboard (M20–M43)

```text
SQLite event store
       |
       v
Atomic Bronze CSV export + SHA-256 manifest
       |
       v
Explicit one-shot dbt DuckDB build
       |
       v
Staging, session and daily marts
       |
       v
Eight semantic quality checks -> success or failure report
```

The one-shot batch is invoked explicitly, not scheduled. The quality gate blocks a successful batch result if any check fails. Run reports and bounded retries preserve separate attempt workspaces. A separate Streamlit application reads a Bronze-format CSV and computes session-cohort metrics. CI validates cross-engine parity, real broker integration and AppTest rendering in dedicated workflows.

**Not implemented as a continuously deployed service:** Airflow orchestration, direct Kafka-to-warehouse continuous ingestion, distributed warehouse infrastructure, cloud monitoring SLAs and automated production recovery.

See [M43 enforced quality](M43_ENFORCED_WAREHOUSE_QUALITY.md), [M44 clean install](M44_REPRODUCIBLE_SETUP.md) and [release acceptance checklist](RELEASE_CHECKLIST.md).
