# PulseForge monitoring, observability and recovery safety

**Status:** Implemented local monitoring modules with tests. Continuous production observability and automatic self-healing are **not enabled**.

## Purpose

Monitoring evaluates source database integrity, event/customer counts, run status, quality report freshness, and analytics summaries. Quality assessments and alerts can be persisted as monitoring snapshots through explicitly invoked components.

## Components

| Module | Responsibility |
| --- | --- |
| `metrics_collector.py` | Read-only metrics from configured SQLite sources, run log, and quality reports |
| `quality_monitor.py` | Evaluate monitoring quality conditions |
| `alert_engine.py` | Produce structured alerts |
| `snapshot_store.py` | Build, store, and retrieve monitoring snapshots |
| `api.py` | Read-only monitoring API |
| `run_identity.py`, `run_consistency.py` | Verify simulation run identity and data consistency |
| `safe_orchestrator.py` | Fail-closed, read-only monitoring preview |
| `self_healing_orchestrator.py` | Preview-only recovery decision planning |
| `recovery_policy.py`, `recovery_controller.py`, `recovery_executor.py` | Recovery policy and explicitly controlled execution helpers |
| `run_level_store.py` | Run-level snapshot deduplication support |

## Monitoring architecture

```text
Configured event/customer SQLite databases + daily run log
                         |
                         v
                Read-only metrics collector
                         |
                         v
               Quality monitor + alert engine
                         |
                         v
                Monitoring snapshot builder
                         |
            +------------+------------+
            |                         |
            v                         v
  Explicit snapshot store       Preview-only safety planning
            |
            v
      Read-only monitoring API
```

Building a snapshot is not the same as persisting one. Preview orchestration does not persist monitoring snapshots or execute recovery.

## API endpoints

| Method | Endpoint | Behavior |
| --- | --- | --- |
| GET | `/monitoring/health` | Checks monitoring SQLite database availability and integrity; returns 503 if unavailable |
| GET | `/monitoring/latest` | Returns latest persisted snapshot, or 404 when none exists |
| GET | `/monitoring/history?limit=10` | Returns recent snapshot summaries; `limit` must be between 1 and 100 |

**Important:** Monitoring `/health` reports monitoring database availability, **not** the health of the full event-processing platform. The monitoring API does not create snapshots merely by being started.

## Source paths and operational safety

Monitoring modules commonly default to:

- Event database: `data/automation/events.db`
- Customer database: `data/automation/customers.db`
- Run log: `data/automation/daily_runs.jsonl`
- Quality reports: `reports/quality/`
- Snapshot database: `data/monitoring/monitoring.db`

Other application modules may use `data/storage/` defaults. Verify paths before invoking any command; the defaults are not interchangeable. Read-only collectors open source SQLite databases in read-only mode. Snapshot persistence and recovery execution are separate operations and require deliberate authorization.

## Safety and recovery boundaries

- `safe_orchestrator.py` rejects non-preview mode and enabled automatic recovery.
- `self_healing_orchestrator.py` rejects execution mode, persistence, and automatic recovery activation.
- Run consistency is rechecked during preview planning.
- Recovery policy and controller modules require explicit authorization for applicable operations.
- Critical recovery is denied by the safety controls.
- Production automatic recovery is not activated, and the scheduler is not integrated with production self-healing.

See [M18 checkpoint](../../docs/M18_AUTOMATED_MONITORING.md) for test history, remaining limitations, and activation checklist.

## Verification and limitations

The published GitHub Actions test workflow runs pytest on Ubuntu / Python 3.12 and passed for commit `84f114aaea6079124e9a453a1ecfea42fca09295`. This is not a live operational health assessment.

Known limitations include lack of continuous snapshot generation, no automated monitoring API deployment, no complete streaming health coverage, and preview-only self-healing. Some legacy snapshot stores have schema-dependent deduplication behavior; `run_level_store.py` is preferred for run-level deduplication.

## Relevant documentation

- [Architecture](../../docs/architecture.md)
- [M18 automated monitoring](../../docs/M18_AUTOMATED_MONITORING.md)
- [Root README](../../README.md)
