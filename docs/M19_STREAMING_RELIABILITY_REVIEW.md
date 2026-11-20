# M19 — Streaming Reliability: Engineering Review

**Branch:** `feature/m19-streaming-reliability`  
**Scope:** M19.1–M19.6, isolated Kafka/Redpanda reliability verification  
**Status:** Engineering review documented; merge is intentionally deferred.

## Verified evidence

- **M19.3 (Windows / Python 3.10):** user-provided pytest output: 2 passed in 3.10 seconds.
- **M19.4 (Windows / Python 3.10):** user-provided pytest output: 4 passed in 3.29 seconds.
- **M19.5 (GitHub Actions):** user-provided Actions screenshot shows green successful `M19 Redpanda integration #1` (29 seconds) and standard `tests #19` (21 seconds), both for commit `3045ee3`.
- The screenshot confirms successful workflow conclusions; it is not a substitute for archived per-step logs or coverage measurement.

## Implemented protections

1. Broker integration tests require `PULSEFORGE_RUN_BROKER_TESTS=1` and a dedicated loopback bootstrap on port `19093`.
2. Disposable Redpanda Compose environment uses a separate project, port, and no persistent/shared volume.
3. Each test creates UUID-scoped source and DLQ topics, a unique consumer group, and a temporary SQLite database.
4. Valid event processing persists to SQLite before committing Kafka offsets.
5. Restart tests simulate offset-commit failure, then use a new consumer with the same group and SQLite database to verify replay and duplicate suppression.
6. Invalid-event tests confirm DLQ routing, zero SQLite rows, and possible duplicate DLQ delivery on replay.
7. A separate GitHub Actions workflow starts the test broker, waits for metadata readiness, runs tests, and cleans up even on failure.

## Limitations and follow-up risks

| Priority | Finding | Impact / proposed follow-up |
| --- | --- | --- |
| High | `SQLiteEventStore.insert_event` and bulk insert use `INSERT OR IGNORE`. Same `event_id` with a different payload is silently classified as a duplicate. | Add payload conflict detection and a deterministic policy before production claims. |
| Medium | DLQ publication and source-offset commit are not atomic. Replay may publish duplicate DLQ records. | Preserve source topic/partition/offset as a downstream deduplication key; document at-least-once DLQ semantics. |
| Medium | Restart tests inject exceptions in `_commit_checked`; they do not interrupt the broker or kill a consumer process. | Add broker outage, consumer termination, and recovery tests in a later hardening milestone. |
| Medium | Tests use a single broker and one-partition test topics. | Add partition, rebalance, and concurrent-consumer tests before distributed production claims. |
| Low | The dedicated workflow uses path filters. Some unrelated changes may not trigger broker tests on push. | Require the workflow on protected PRs or broaden triggers if relevant. |
| Low | No quantified integration coverage or load/soak test evidence recorded. | Add measured coverage, longer-duration tests, and performance thresholds when required. |

## Release decision

**M19 test implementation and documented review are complete.** The demonstrated guarantee is **at-least-once event processing with idempotent SQLite inserts for repeated event IDs under the tested scenarios**, not exactly-once end-to-end delivery.

**Do not merge automatically.** The user's local repository contains pre-existing modified files, including `services/generator/journey_generator.py`, which should not be reset or discarded. Review the branch diff, confirm required checks and branch protection, and obtain an explicit merge decision. The known event-ID conflict behavior remains a tracked follow-up rather than an unannounced production change.

## Reproduction

```powershell
docker compose -p pulseforge-m19-test -f docker-compose.m19-test.yml up -d
$env:PULSEFORGE_RUN_BROKER_TESTS = "1"
$env:PULSEFORGE_TEST_BOOTSTRAP = "127.0.0.1:19093"
python -m pytest -v -s tests/integration/test_m19_broker_roundtrip.py
docker compose -p pulseforge-m19-test -f docker-compose.m19-test.yml down
Remove-Item Env:PULSEFORGE_RUN_BROKER_TESTS
Remove-Item Env:PULSEFORGE_TEST_BOOTSTRAP
```
