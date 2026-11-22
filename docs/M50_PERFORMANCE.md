# M50 — Synthetic scale smoke

A dedicated GitHub Actions workflow generates 1,000 seeded synthetic sessions, inserts events into disposable SQLite, exports a Bronze CSV, and verifies its SHA-256 manifest and row count. It has a generous 120-second smoke threshold to detect severe regressions on hosted runners, not a production latency SLO.

The test is opt-in via `PULSEFORGE_RUN_M50_PERF=1`; it does not slow the standard pytest workflow. The workflow is reproducible and uses synthetic data only. Actual throughput depends on the CI runner and should not be advertised as a production benchmark.

This is a bounded-scale smoke test, not a sustained-load, concurrency, or endurance benchmark.
