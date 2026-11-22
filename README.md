# PulseForge

**Synthetic Product Intelligence & Data Reliability Platform**

[![Tests](https://github.com/gurusumiran25/pulseforge/actions/workflows/tests.yml/badge.svg)](https://github.com/gurusumiran25/pulseforge/actions/workflows/tests.yml)

PulseForge is an actively developed Python portfolio project exploring synthetic e-commerce event generation, validated ingestion, Kafka-compatible streaming, SQLite persistence, product analytics, data quality, monitoring, and controlled recovery.

**Status:** The repository includes a reproducible synthetic end-to-end portfolio demonstration and isolated broker-backed CI, but it is **not a production-deployed analytics platform**. Live broker integration, continuously deployed monitoring, and automatic production self-healing are not covered by the standard CI workflow.

## Engineering goals

- Model versioned, validated e-commerce events.
- Preserve events safely across API, broker, and storage boundaries.
- Compute session-level funnel and order-level revenue metrics.
- Simulate daily customer activity with run consistency and execution locks.
- Detect data quality problems and produce monitoring snapshots and alerts.
- Require explicit authorization for recovery; fail closed by default.

## Technology

| Concern | Implementation |
| --- | --- |
| Language | Python 3.10+ |
| API | FastAPI, Uvicorn |
| Validation | Pydantic v2 |
| Streaming | Redpanda-compatible Kafka, `confluent-kafka` |
| Persistence | SQLite |
| Analytics | Python, SQL |
| Tests and tooling | pytest, HTTPX, Ruff |
| Local broker configuration | Docker Compose |
| CI | GitHub Actions, Ubuntu / Python 3.12 |

## Implemented capabilities

| Area | Current implementation | Boundary |
| --- | --- | --- |
| Synthetic events | Customer journeys, seeded decision-making, batch JSONL generation | UUIDs and current timestamps mean output is not byte-for-byte deterministic |
| Event contracts | Versioned Pydantic envelope, UTC normalization, event-specific property checks | Schema version 1 |
| Ingestion | `/health`, `/v1/events`, `/v1/events/batch` | Publishing requires a reachable broker; batch sends are not atomic |
| Streaming | Delivery-confirmed producer, consumer, explicit offset commits, dead-letter handling | Live broker validation is separate from standard CI |
| Storage | SQLite event storage, event-ID deduplication, bulk inserts | Local storage, not a warehouse |
| Daily simulation | Customer selection, persona journeys, run ledger, execution locking | Operational runs write data; dry-run is available |
| Analytics | Ordered session funnel; payments, refunds, and revenue by currency | Local Python/SQLite analysis |
| Data quality | Event scanning, integrity checks, scoring, volume anomaly detection | Requires appropriate source databases |
| Monitoring | Metrics, alerts, SQLite snapshots, read-only API | Not continuously deployed |
| Recovery | Run-consistency checks, policy controls, bounded components, preview planning | Production automatic self-healing is **disabled** |

## Architecture

### Streaming path

```text
Synthetic events / API clients
            |
            v
Pydantic event validation
            |
            v
FastAPI ingestion
            |
            v
Redpanda / Kafka-compatible broker
            |
            v
Consumer ---------> Invalid events: dead-letter topic
            |
            v
SQLite event store
            |
            v
Funnel and revenue analytics / data quality checks
```

The consumer commits offsets only after appropriate message handling. An invalid event is routed to the dead-letter topic before the offset is committed. Batch ingestion may partially publish; retrying may produce duplicate broker messages.

### Daily simulation and reliability path

```text
Daily simulation CLI
        |
        v
Execution lock and atomic customer selection
        |
        v
Persona journey generation
        |
        v
SQLite event persistence and run ledger
        |
        v
Consistency checks, quality assessment, metrics and alerts
        |
        v
Preview-only self-healing decisions
```

These are related subsystems, **not** a claim of one continuously deployed production pipeline. See [architecture details](docs/architecture.md).

## Repository map

```text
contracts/                Versioned event contract and validation
services/generator/       Synthetic journeys and batch generation
services/ingestion/       FastAPI ingestion
services/streaming/       Kafka-compatible producer and consumer
services/storage/         SQLite event persistence
services/simulation/      Daily customer simulation and recovery helpers
services/analytics/       Funnel, revenue, Bronze export, batch orchestration and quality gates
services/quality/         Data quality reports and checks
services/monitoring/      Metrics, snapshots, alerts, monitoring and recovery
apps/dashboard/          Streamlit product analytics dashboard
services/monitoring/README.md  Monitoring reference
contracts/events/         Event envelope schema
.github/workflows/        Automated tests
```

## Reproducible portfolio environment

Install the complete portfolio dependency set with `python -m pip install -e ".[dev,portfolio]"`. This includes Streamlit and dbt DuckDB, which are intentionally optional in the core package. The [M44 clean-install workflow](.github/workflows/m44-release-smoke.yml) verifies dependency resolution, dashboard rendering, and the real quality-gated warehouse batch. See [release acceptance checklist](docs/RELEASE_CHECKLIST.md). These are isolated validations, not a deployed service.

## Local setup (fresh, isolated clone)

Prerequisites: Python 3.10+, Git; Docker/Compose only for broker-backed demonstrations.

**Windows PowerShell:**

```powershell
git clone https://github.com/gurusumiran25/pulseforge.git
cd pulseforge
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
```

**macOS / Linux:**

```bash
git clone https://github.com/gurusumiran25/pulseforge.git
cd pulseforge
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
```

These are instructions for an **isolated development clone**, not commands to run against existing operational databases. The standard GitHub Actions workflow installs development dependencies and runs pytest on Ubuntu with Python 3.12.

### Generate a synthetic batch

This command **writes** a JSONL file:

```powershell
python -m services.generator.batch_generator --sessions 1000 --seed 42 --output data/generated/customer_events.jsonl
```

### Preview daily simulation configuration

This command prints configuration without executing the simulation:

```powershell
python -m services.simulation.daily_cli --date 2026-11-16 --customers 100 --seed 42 --dry-run
```

Running the CLI without `--dry-run` writes to configured simulation/event databases and the run log. Review paths and obtain authorization before any operational execution.

### Ingestion API (requires broker for publication)

```powershell
python -m uvicorn services.ingestion.main:app --host 127.0.0.1 --port 8000
```

| Method | Path | Meaning |
| --- | --- | --- |
| GET | `/health` | API process health, **not** broker availability |
| POST | `/v1/events` | Validate and publish a single event |
| POST | `/v1/events/batch` | Validate and publish 1â€“1000 events; partial publication possible |

A Redpanda service definition exists in `docker-compose.yml`, but starting containers, creating topics, and running live Kafka tests are separate, explicitly controlled operations.

### Monitoring API

| Method | Path | Meaning |
| --- | --- | --- |
| GET | `/monitoring/health` | Monitoring database availability/integrity, not full platform health |
| GET | `/monitoring/latest` | Latest persisted monitoring snapshot |
| GET | `/monitoring/history?limit=10` | Recent snapshot summaries (limit 1â€“100) |

See [monitoring documentation](services/monitoring/README.md) for prerequisites and limitations.

## Event catalogue

The eight recognized event names are `page_view`, `search_performed`, `product_viewed`, `add_to_cart`, `checkout_started`, `payment_succeeded`, `payment_failed`, and `order_refunded`.

See [event catalogue](docs/event_catalogue.md) and `contracts/event_validation.py` for required fields and validation rules.

## Testing and safety

The standard CI workflow runs `python -m pytest` on Ubuntu / Python 3.12. Dedicated CI workflows separately test real Redpanda delivery (M26/M33), dbt quality gates (M43), clean-install dashboard and warehouse smoke tests (M44), and the real synthetic portfolio demo (M45). These checks do not constitute production deployment or browser-level UI verification.

A dedicated GitHub Actions workflow verifies a disposable live Redpanda broker (M26); standard CI alone does not. CI success does **not** prove production deployment or all operational paths are error-free.

Recovery planning is preview-only by default. Production automatic self-healing is not enabled, and scheduler integration requires separate approval. Do not commit credentials, real customer data, operational databases, or sensitive reports.

## Roadmap

- [x] Event validation and synthetic generation
- [x] FastAPI ingestion modules
- [x] Kafka-compatible producer and consumer modules
- [x] SQLite persistence and duplicate handling
- [x] Funnel and revenue analytics
- [x] Daily customer simulation and execution locks
- [x] Data quality, monitoring, and preview-safe recovery foundations
- [x] GitHub Actions pytest workflow
- [x] Repeatable isolated real-broker integration validation (M26 GitHub Actions)
- [x] Bronze/Silver/Gold warehouse and dbt models (M20/M27)
- [x] Streamlit analytics dashboard and configurable CSV source (M21–M29)
- [ ] Airflow orchestration
- [ ] Continuous monitoring and production deployment hardening

## Warehouse and dashboard

The repository includes dbt DuckDB Bronze/Silver/Gold transformations, a one-shot SQLite-to-Bronze batch builder with integrity manifests, a semantic quality gate, and a Streamlit dashboard. The dashboard reads Bronze-format CSV, not DuckDB directly. See [M43 quality-gate documentation](docs/M43_ENFORCED_WAREHOUSE_QUALITY.md) and [M44 setup](docs/M44_REPRODUCIBLE_SETUP.md).

## Portfolio demonstration

**One-command synthetic demo:** after installing `.[dev,portfolio]`, run `python -m services.analytics.portfolio_demo --output-root /tmp/pulseforge-demo --sessions 20` with a new empty output directory. This executes real SQLite → verified Bronze → dbt DuckDB → semantic quality → offline health and dashboard metric parity, writing a JSON summary. It does **not** start a broker or web server. See [M45 instructions](docs/M45_PORTFOLIO_DEMO.md), [portfolio evidence and interview talking points](docs/PORTFOLIO_DEMO.md) and [release checklist](docs/RELEASE_CHECKLIST.md). The real-broker and warehouse/dashboard parity checks are isolated CI integrations, **not** a continuously deployed production pipeline.

## Further documentation

- [Architecture](docs/architecture.md)
- [Event catalogue](docs/event_catalogue.md)
- [Monitoring reference](services/monitoring/README.md)
- [M18 safety and self-healing checkpoint](docs/M18_AUTOMATED_MONITORING.md)
- [Local-first decision](docs/decisions/0001-local-first.md)

**Project status:** Portfolio release hardening; synthetic data only. Final release acceptance and tagging remain pending.
