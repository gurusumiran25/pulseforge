# PulseForge - Monitoring and Observability

## Overview
Milestone 17 adds metrics collection, quality monitoring,
deterministic alerts, SQLite snapshots, and a FastAPI interface.

## Architecture
Source SQLite databases -> Metrics Collector
Metrics Collector -> Quality Monitor + Alert Engine
Quality Monitor + Alert Engine -> Snapshot Store -> Monitoring API

## Components
- metrics_collector.py: reads operational and analytics metrics.
- quality_monitor.py: evaluates integrity, freshness, and quality.
- alert_engine.py: produces structured deterministic alerts.
- snapshot_store.py: persists and retrieves monitoring snapshots.
- api.py: exposes monitoring endpoints.

## API Endpoints
- GET /monitoring/health: monitoring database health.
- GET /monitoring/latest: most recent saved snapshot.
- GET /monitoring/history?limit=10: historical snapshots.
- History limit accepts values from 1 to 100.

## Persistence
- Snapshot database: data/monitoring/monitoring.db
- SQLite connections are explicitly closed.
- Source database reads use read-only connections.

## Health Assessment
- Quality states: HEALTHY, DEGRADED, CRITICAL, UNKNOWN.
- Checks include integrity, report coverage, score, and age.
- Snapshot scope currently includes storage and data_quality.

## Validation
- Full regression: 198 tests passed using pytest.
- Monitoring-specific suite: 28 tests passed.
- Three SQLite databases passed integrity checks.

Run the full suite:
python -m pytest tests -q

## Known Limitations
- Snapshots are not yet generated continuously.
- Monitoring API deployment is not yet automated.
- Monitoring health does not represent all platform services.
- A stale quality report can produce DEGRADED status.
- Starlette test-client dependency emits a deprecation warning.

## Future Enhancements
- Automatically generate snapshots after scheduled runs.
- Refresh quality reports before monitoring assessment.
- Add ingestion and streaming health checks.
- Add alert delivery, history charts, and dashboards.

## Status
M17 provides a tested local monitoring foundation.
Continuous production observability is not yet implemented.
