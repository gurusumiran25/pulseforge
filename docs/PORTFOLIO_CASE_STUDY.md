# PulseForge | Product analytics and data reliability case study

## Executive summary

PulseForge is a synthetic e-commerce analytics engineering portfolio project. It demonstrates how validated behavioral events can become trustworthy product metrics, with explicit reliability controls across ingestion, storage, transformation and publication. It is not a production service or a claim of commercial impact.

## Business problem and objectives

Product analysts need to identify conversion friction, understand payment outcomes and segment customers without relying on inconsistent event data. The project models these needs through session analytics, currency-separated payment metrics, RFM segmentation and visible data freshness. The engineering objective is to make the results reproducible and reject corrupted inputs rather than silently present misleading numbers.

## Architecture and responsibilities

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Generation | Python | Synthetic journeys and eight event types |
| Contract and API | Pydantic, FastAPI | Validate event envelopes and event-specific properties |
| Messaging | Redpanda, confluent-kafka | Delivery-confirmed publication and explicit consumer offsets |
| Persistence | SQLite | Event storage and event-ID deduplication |
| Warehouse | Bronze CSV, dbt, DuckDB | Integrity-checked exports and Silver/Gold transformations |
| Analytics | SQL, Python, Streamlit | Session metrics, payments and customer segments |
| Reliability | GitHub Actions, quality gates | Scheduled publication, freshness checks and bounded retries |

The broker-backed integration and scheduled public analytics batch are separate paths. The public dashboard reads verified CSV rather than querying DuckDB directly. See [architecture](architecture.md) and [demo evidence](PORTFOLIO_DEMO.md).

## Measured demonstration snapshot

The [published status](../data/public/status.json) recorded the following on 2026-11-25 UTC. This is a historical synthetic snapshot; the linked file changes as new data is published.

| Metric | Value | Interpretation |
| --- | ---: | --- |
| Events | 2,634 | Generated behavioral records |
| Sessions | 560 | 40 sessions/day across 14 days |
| Sessions with payment | 240 | Synthetic paid-session count |
| Paid-session share | 42.86% | 240 / 560, not real customer conversion |
| Semantic quality checks | 8 | Publication status reported passed |

These numbers demonstrate the analytics pipeline, not actual business uplift, production throughput or real customer behavior.

## Engineering decisions and tradeoffs

- Explicit offset commits and event-ID deduplication address replay risks without claiming exactly-once end-to-end delivery. Batch publication may partially succeed.
- SQLite and DuckDB keep the demonstration reproducible on modest infrastructure; they are not substitutes for a distributed production warehouse.
- SHA-256 manifests, semantic quality gates and independent freshness monitoring help prevent silent publication of invalid data.
- Bounded CDN retries handle transient propagation delays; integrity failures remain fail-closed.
- Recovery is preview-only. Free hosting may sleep, and scheduled jobs have no guaranteed uptime or punctuality.

## Demonstration and validation

Use the [README](../README.md) to install the portfolio extras in an isolated Python environment. The one-command demo exercises SQLite, Bronze, real dbt, quality checks and dashboard metric parity. Dedicated CI separately exercises real broker integration. The [public dashboard](https://pulseforge-analytics.streamlit.app/) is available as a demo URL; independent [hosted Chromium browser acceptance](https://github.com/gurusumiran25/pulseforge/actions/runs/46119491797) and [exact-SHA release candidate verification](https://github.com/gurusumiran25/pulseforge/actions/runs/46119216023) both passed on 2026-11-28 for commit `920e3f284b8642301bbf13ce5184a79101b51f95`. Official release publication remains pending. See [release checklist](RELEASE_CHECKLIST.md).

## Interview discussion

**Why Kafka?** To decouple ingestion from consumption and demonstrate delivery confirmation, replay and offset management.

**Why dbt?** To make warehouse transformations and semantic checks explicit and reproducible.

**How do you avoid misleading KPIs?** Define session/cohort semantics, separate currencies, validate source integrity and reconcile independent metric implementations.

**What would change at production scale?** Evaluate durable distributed storage, orchestration, observability, secrets management, load testing and stronger delivery guarantees based on measured requirements.

## Portfolio takeaway

PulseForge demonstrates business problem framing, Python and SQL analytics, API contracts, event-driven integration, warehouse modeling, dashboard development and data reliability. Its strongest evidence is reproducible synthetic demonstrations and documented CI, not unverified production claims.
