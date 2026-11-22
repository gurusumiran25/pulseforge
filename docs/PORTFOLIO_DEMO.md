# PulseForge — Portfolio demo and evidence

**One-line pitch:** A synthetic product intelligence and data reliability platform connecting validated event ingestion, Kafka-compatible streaming, durable local storage, warehouse transformations, cohort analytics, and a Streamlit dashboard.

## Demonstrable architecture

```text
Synthetic customer journeys
   |                 |
   v                 v
FastAPI batch API    Disposable SQLite / Bronze CSV
   |                 |
   v                 v
Redpanda broker      dbt + DuckDB
   |                 |
   v                 v
Kafka consumer       Silver / Gold marts
   |                 |
   v                 v
SQLite event store   Streamlit metrics (CSV source)
```

The two paths are **separately validated integrations**, not one deployed continuous production pipeline. The Streamlit dashboard calculates metrics from the Bronze-format CSV, rather than querying DuckDB directly.

## Evidence by milestone

| Milestone | Verified scope | Not verified |
| --- | --- | --- |
| M19 | Redpanda integration workflow | Production broker operation |
| M20 | dbt DuckDB Bronze/Silver/Gold models and tests | Streaming warehouse ingestion |
| M21–M23 | Dashboard calculations, cohort filtering, dbt parity | Browser-level UI testing |
| M24 | Generated journeys → SQLite → SQL views | API and broker |
| M25 | FastAPI batch → producer double → consumer handler → SQLite | Real Kafka |
| M26 | FastAPI batch → real Redpanda → real consumer → SQLite → SQL views | dbt and dashboard in same network test |
| M27 | Generated events → SQLite views → CSV → dbt DuckDB parity | Continuous Kafka-to-dbt |
| M28 | Generated dataset → SQLite/dbt → dashboard metrics parity | Streamlit rendering |
| M29 | Configurable CSV source for Streamlit | Direct warehouse query |
| M30–M34 | Portfolio documentation, Streamlit AppTest, atomic Bronze export, real broker-to-dbt and dashboard parity | Always-on operation |
| M35–M40 | Explicit warehouse batch, snapshot refresh, SHA-256 manifest, manifest gate, structured run reports, bounded retries | Distributed scheduler and recovery |
| M41–M43 | Offline health checks, eight semantic checks and enforced real dbt quality gate | Continuous production monitoring |
| M44 | Clean-install dependency extras and dashboard/warehouse smoke CI | Fully pinned dependency lock |
| M45 | One-command real synthetic SQLite → Bronze → dbt → quality → health → dashboard metric parity | Live broker in same command |

## Demo narrative for interviews

1. Describe the event envelope: schema version, UTC timestamps, session/user identity, and event-specific properties.
2. Explain delivery guarantees: broker-confirmed producer writes, explicit consumer offset commits, event-ID deduplication, and non-atomic batch publication.
3. Show SQL analytics: session-start UTC cohort definitions and stage-presence metrics, which are **not** an ordered funnel.
4. Explain parity checks across independent implementations on generated data, not only fixed demo rows.
5. Discuss reliability tradeoffs: SQLite is local persistence; the platform is not production deployed; automated recovery remains preview-safe.

## Recruiter-ready résumé wording (verify before using)

**PulseForge — Synthetic Product Intelligence & Data Reliability Platform** | Python, FastAPI, Pydantic, Redpanda/Kafka, SQLite, SQL, dbt, DuckDB, Streamlit, GitHub Actions

- Built a versioned synthetic event pipeline with FastAPI batch ingestion, Kafka-compatible messaging, consumer offset commits, SQLite persistence, and deduplication.
- Implemented Bronze/Silver/Gold analytics with dbt/DuckDB and tested daily session-cohort metric consistency against SQLite SQL views and dashboard calculations.
- Automated integration checks for a real Redpanda broker and generated-data warehouse/dashboard parity using isolated GitHub Actions workflows.

These are **project implementation claims**, not claims of production scale, external users, or deployed revenue impact.

## One-command demo (synthetic data)

Install `.[dev,portfolio]` and run `python -m services.analytics.portfolio_demo --output-root /tmp/pulseforge-demo --sessions 20` using an empty output directory. This generates a SQLite event store, Bronze snapshot and manifest, real dbt DuckDB marts, run report, health validation and JSON summary. The demo verifies event/session/payment counts against the dashboard metric implementation. See [M45 instructions](M45_PORTFOLIO_DEMO.md) and [release checklist](RELEASE_CHECKLIST.md). Real Redpanda ingestion remains an independent dedicated integration workflow.

## Known gaps / next milestones

- Streamlit AppTest rendering is covered by dedicated CI; deployed browser-level visual UX remains unverified.
- Direct Kafka-to-warehouse streaming ingestion and orchestration.
- Recovery after consumer rebalance and sustained load tests.
- Production secrets, observability, hosting, and scaling.

## Safety

All published demos use synthetic data. Avoid committing credentials, customer information, operational databases, or locally generated artifacts.
