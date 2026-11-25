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

## M69–M71 publication and release evidence

- M69 [PR #51](https://github.com/gurusumiran25/pulseforge/pull/51) merged after two successful PR checks; its scoped publisher-code push trigger is intended to bootstrap a new feed without self-triggering on generated data commits.
- The 2026-11-23 public status now contains `payment_sidecar` with schema version 1, **241** rows and a SHA-256 digest. Its `bronze_sha256` matches the SHA in `latest_bronze.manifest.json`. The published CSV file exists. This is evidence of one payment publication, not consecutive daily scheduled executions or browser UI acceptance.
- M70 [PR #52](https://github.com/gurusumiran25/pulseforge/pull/52) merged after eight successful PR workflows, including Streamlit widget rendering and portfolio release acceptance. These are PR-head CI checks, not evidence for a future tagged release SHA.
- Browser-level verification of the hosted Streamlit customer analytics tables remains **open**; follow [M71 acceptance instructions](M53_STREAMLIT_CLOUD.md#m71-live-customer-analytics-acceptance).
- Do not mark the repository as fully production-deployed: the public feed is synthetic and the broker/monitoring services are not established as continuously hosted.

## Scope boundary

The target is a **reproducible portfolio demonstration** using synthetic data, not an always-on production service. Airflow, distributed storage, continuous cloud deployment and operational SLAs are not required to declare the portfolio release complete. They remain optional follow-on engineering work.

Do not mark any checkbox complete solely because a source file exists. Verify each acceptance criterion against CI or a documented test run.

## Current verification evidence (2026-11-23)

- M54 PR [#36](https://github.com/gurusumiran25/pulseforge/pull/36) merged after eight successful PR workflows, including the standard tests, dashboard checks, daily-feed integration and M52 release acceptance.
- M55 PR [#37](https://github.com/gurusumiran25/pulseforge/pull/37) merged after eight successful PR workflows, including real Redpanda, the M55 health monitor, M52 acceptance, real warehouse quality and the one-command demo.
- `data/public/status.json` on main reports a successful 2026-11-23 publication with 2,669 events, 560 sessions and eight quality checks. This proves one published snapshot, **not** multiple consecutive scheduled runs.
- These are PR-head checks, not independent evidence that all workflows passed on the final tagged release SHA. Keep the release checklist unchecked until each exact release gate has independently verified evidence.
- Remaining external gates: confirm consecutive daily publication and independent health runs; deploy and visually test Streamlit Community Cloud; audit release SHA, repository contents and security; publish a tagged release with documented limitations.

## M72–M77 final verification status

- M72 [PR #54](https://github.com/gurusumiran25/pulseforge/pull/54): independent feed health is chained to successful publisher completion via `workflow_run`.
- M73 [PR #55](https://github.com/gurusumiran25/pulseforge/pull/55) and M75 [PR #57](https://github.com/gurusumiran25/pulseforge/pull/57): tracked-filename hygiene gate and strict four-file public feed allowlist. This is **not** a complete secrets-content or Git-history scan.
- M74 [PR #56](https://github.com/gurusumiran25/pulseforge/pull/56) and M76 [PR #58](https://github.com/gurusumiran25/pulseforge/pull/58): remote CDN integrity smoke and status/metrics parity checks. Successful PR tests do **not** prove the scheduled remote smoke has run successfully.
- M77 adds a manual **release candidate verification** workflow: from Actions, select `M77 release candidate verification`, enter the exact 40-character candidate commit SHA, and retain the resulting run URL. It checks the exact checkout SHA, clean install, portfolio tests, tracked-artifact hygiene, local published feed and remote CDN. The run may fail if the feed is stale; do not waive freshness without recording why.
- Before tagging, separately verify Redpanda workflow on the **same** candidate SHA, Streamlit browser acceptance with screenshot, at least two consecutive scheduled daily publisher runs and their independent monitors, and repository content/history security review.
- **Do not create a release tag or check off the eleven gates merely because M77 workflow exists.** A successful run with a recorded candidate SHA and additional external evidence is required.

## M82–M85 release hardening and hosted acceptance

- M82 [PR #64](https://github.com/gurusumiran25/pulseforge/pull/64): Streamlit Cloud configuration regression tests and four-artifact architecture documentation merged with eight successful checks.
- M83 [PR #65](https://github.com/gurusumiran25/pulseforge/pull/65): conservative tracked-file content scanner merged after all three checks passed. Its synthetic fixture is intentionally excluded; this does not establish historical secret hygiene.
- M84 [PR #66](https://github.com/gurusumiran25/pulseforge/pull/66): bounded CDN retries for both verified feeds merged after nine successful checks; integrity failures still fail closed after retries.
- M85 enables a real hosted Chromium browser acceptance run after relevant changes land on main, in addition to manual dispatch. The PR event still executes only offline regression tests. **A workflow definition is not live deployment evidence**: record the main-branch browser run URL and screenshot artifact, confirm all expected tables render, and keep the hosted acceptance gate open if it fails.
- If hosted acceptance reports local CSV mode, configure `PULSEFORGE_PUBLIC_FEED = "1"` in Streamlit Community Cloud app secrets and restart/redeploy the app. Do not put credentials or other secrets into source control.
- Do not tag v1.0.0 until M77 exact-SHA acceptance, M78/M79 scheduled evidence, real Redpanda integration and hosted browser checks are independently verified.

## Latest verified pre-release evidence (2026-11-25 UTC)

- [M52 portfolio acceptance](https://github.com/gurusumiran25/pulseforge/actions/runs/45691522650): clean install, pip check, enabled portfolio integration suite and lint passed on PR #76.
- [Real broker-to-dbt integration](https://github.com/gurusumiran25/pulseforge/actions/runs/45691975819): actual Redpanda-to-dbt test passed on PR #77.
- [Historical credential scan](https://github.com/gurusumiran25/pulseforge/actions/runs/45692657525): Gitleaks scanned 335 reachable commits with no detected leaks on PR #78.
- [Real hosted Chromium acceptance](https://github.com/gurusumiran25/pulseforge/actions/runs/45694260162): all five required text checks passed with no forbidden error markers on PR #79. [Screenshot artifact](https://github.com/gurusumiran25/pulseforge/actions/runs/45694260162/artifacts/15061060277). This supersedes the earlier PR-only hosted acceptance limitation, but is not exact final main SHA evidence.
- The November 25 public status reports 2,634 events, 560 sessions, 240 paid sessions and eight quality checks. Consecutive scheduled publisher and monitor run evidence remains to be reconciled.

The candidate review deliberately triggers M52, M33, history scanning and real hosted browser acceptance. Keep final SHA and tag gates open until independently verified; do not interpret this evidence as production certification.
