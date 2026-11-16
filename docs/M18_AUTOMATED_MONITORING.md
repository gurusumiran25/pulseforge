# PulseForge M18 — Automated Monitoring and Self-Healing

## Project status

Engineering checkpoint: Preview-safe implementation validated.

Production self-healing: NOT ENABLED.

The existing daily simulation scheduler remains unchanged.

## Overview

M18 extends PulseForge with:

- Automated monitoring and health assessment
- Simulation run identity and consistency verification
- Quality-report generation and refresh
- Failure classification
- Recovery authorization and default-deny controls
- Bounded retry execution
- Idempotent monitoring snapshot storage
- Preview-only self-healing orchestration

## Architecture

Completed simulation
    |
    v
Run identity verification
    |
    v
Database and ledger consistency
    |
    v
Metrics collection
    |
    v
Monitoring snapshot and alerts
    |
    v
Recovery policy evaluation
    |
    +-- Preview-only monitoring plan
    |
    +-- Explicitly authorized isolated recovery
    |
    +-- Run-level idempotent storage

This describes the tested components, not an active
production self-healing workflow.

## Core components

| Module | Responsibility |
| --- | --- |
| automated_runner.py | Monitoring runner |
| compatible_store.py | Earlier M17-compatible storage |
| failure_classifier.py | Failure classification |
| idempotent_store.py | Schema-dependent idempotency |
| integration_preview.py | Isolated integration preview |
| post_run_pipeline.py | Post-run monitoring workflow |
| quality_refresh.py | Quality-report refresh |
| recovery_controller.py | Authorized quality recovery |
| recovery_executor.py | Bounded retry and audit |
| recovery_policy.py | Recovery decisions |
| run_consistency.py | Ledger and database consistency |
| run_identity.py | Completed run identity |
| run_level_store.py | Run-level deduplicated storage |
| safe_orchestrator.py | Read-only monitoring preview |
| self_healing_orchestrator.py | Fail-closed self-healing planner |

## Safety controls

- Recovery is disabled by default.
- Non-preview orchestration is rejected.
- Unauthorized monitoring persistence is rejected.
- Critical quality recovery is denied.
- Event-count and run-identity changes are detected.
- Monitoring snapshot errors propagate.
- Quality recovery was validated using temporary directories.
- Snapshot persistence was validated using temporary databases.
- Run-level duplicate prevention was verified.
- M17 monitoring reader compatibility was verified.

## Verification results

Stage 11I: Integrated isolated recovery passed.

Stage 11J: Safe orchestrator passed.

Stage 11K: Fault injection passed.

Stage 11L: Integration validation passed.

Stage 12A: 198 baseline tests passed.

Stage 12B: 15 M18 modules inventoried.

Stage 12C: 11 permanent safety tests passed.

Final regression: 209 tests passed, 1 deprecation warning.

## Known limitations

- Production automatic recovery is not enabled.
- The scheduler does not execute M18 self-healing.
- Preview orchestration does not persist snapshots.
- The older compatible_store.py has a cross-schema
  duplicate risk for the same logical run.
- The older idempotent_store.py uses schema-dependent keys.
- run_level_store.py is preferred for run-level deduplication.
- Not all isolated integration scenarios have permanent tests.
- Production activation requires separate validation and approval.

## Test commands

Permanent M18 tests:

    python -m pytest -q -p no:cacheprovider tests/test_m18_safety_contracts.py

Full regression:

    python -m pytest -q -p no:cacheprovider

## Production activation checklist

1. Review recovery authorization.
2. Validate write paths in isolated environments.
3. Confirm database compatibility.
4. Verify concurrency and rollback behavior.
5. Review audit logging.
6. Validate scheduler integration separately.
7. Obtain explicit approval before activation.
8. Monitor the first authorized production execution.

## Git checkpoint rules

Stage only reviewed M18 modules, permanent M18 tests,
and this documentation.

Exclude production databases, reports, simulation logs,
scheduler backups, and unrelated changes.

Never use git add . for this checkpoint.