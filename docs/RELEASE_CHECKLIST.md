# PulseForge portfolio release acceptance checklist

A green standard pytest workflow alone does **not** establish release readiness.

## Required release gates

- [ ] Clean Python 3.12 environment installs `.[dev,portfolio]` and passes `pip check`
- [ ] Standard Python tests pass on the release commit
- [ ] Real Redpanda ingestion and consumer integration passes
- [ ] Real SQLite -> Bronze -> dbt DuckDB -> quality-gated warehouse build passes
- [ ] Streamlit AppTest renders dashboard metrics and handles invalid sources
- [ ] A single documented demonstration produces verifiable event, session and daily metrics
- [ ] Failure injection tests cover malformed inputs, nonretryable integrity failures and bounded retries
- [ ] README and architecture reflect the implementation and distinguish isolated tests from deployment
- [ ] GitHub Actions workflows are green on the **release candidate SHA**
- [ ] Repository excludes credentials, customer data, operational databases and generated artifacts
- [ ] A tagged release includes known limitations, setup and demo instructions

## Release evidence and CI

The [M52 acceptance workflow](../.github/workflows/m52-release-acceptance.yml) runs a clean Python 3.12 install, dependency check, full pytest suite, real dbt build, synthetic one-command demo, deliberate semantic corruption regression, and 1,000-session integrity/performance smoke. The separate Redpanda integration workflow is required to verify broker delivery; its exact path and green status must be checked on the final release candidate.

M49 fixes deterministic retry classification; M50 adds bounded synthetic scale; M51 adds an opt-in append-only incremental publisher that exposes CSV and manifest together via directory rename. M51 is **not** integrated into the default dbt one-shot batch and is not a multi-writer distributed transaction.

Do not check off the release-commit or tagged-release requirements until the exact SHA and published release are independently verified.

## Scope boundary

The target is a **reproducible portfolio demonstration** using synthetic data, not an always-on production service. Airflow, distributed storage, continuous cloud deployment and operational SLAs are not required to declare the portfolio release complete. They remain optional follow-on engineering work.

Do not mark any checkbox complete solely because a source file exists. Verify each acceptance criterion against CI or a documented test run.

## Current verification evidence (2026-11-23)

- M54 PR [#36](https://github.com/gurusumiran25/pulseforge/pull/36) merged after eight successful PR workflows, including the standard tests, dashboard checks, daily-feed integration and M52 release acceptance.
- M55 PR [#37](https://github.com/gurusumiran25/pulseforge/pull/37) merged after eight successful PR workflows, including real Redpanda, the M55 health monitor, M52 acceptance, real warehouse quality and the one-command demo.
- `data/public/status.json` on main reports a successful 2026-11-23 publication with 2,669 events, 560 sessions and eight quality checks. This proves one published snapshot, **not** multiple consecutive scheduled runs.
- These are PR-head checks, not independent evidence that all workflows passed on the final tagged release SHA. Keep the release checklist unchecked until each exact release gate has independently verified evidence.
- Remaining external gates: confirm consecutive daily publication and independent health runs; deploy and visually test Streamlit Community Cloud; audit release SHA, repository contents and security; publish a tagged release with documented limitations.
