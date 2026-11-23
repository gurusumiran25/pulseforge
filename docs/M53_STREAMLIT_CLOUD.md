# M53 — Scheduled synthetic feed + Streamlit Community Cloud

## Architecture

GitHub Actions runs the daily publisher at **02:30 UTC (08:00 IST)**, with a manual `workflow_dispatch` option. The run generates a fresh **rolling 14-day** synthetic dataset (40 sessions/day), inserts into a disposable SQLite database, executes real dbt DuckDB marts, verifies the eight semantic checks and warehouse health, reconciles dashboard counts, then commits **Bronze CSV + SHA-256 manifest + payment sidecar CSV + status JSON together** to `data/public/` in one Git commit. No operational database, credentials or customer data is published.

The Streamlit Community Cloud app uses the fixed public raw GitHub URL and verifies CSV SHA-256, row count, and a timezone-aware publication timestamp against the manifest. Missing, malformed, naive, or more than ten minutes future-dated timestamps fail closed; feeds older than 36 hours remain visible with a stale warning. Its cache expires every **3600 seconds**, so an already-running app can fetch a newer feed on its next rerun after expiry. GitHub Actions scheduled jobs may be delayed or disabled; there is **no guarantee of a refresh at exactly 08:00 IST**. GitHub raw CDN cache propagation may briefly produce a mismatch, which fails closed instead of displaying unverified data.

## Deploy Streamlit Community Cloud (account owner action)

1. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with the GitHub account authorized for `gurusumiran25/pulseforge`.
2. Select the repository, branch `main`, entry point `apps/dashboard/streamlit_app.py`. Set Python 3.12 if offered. The repository's `requirements.txt` or equivalent installation configuration must be recognized by the deployment.
3. In the app's advanced settings / secrets, add `PULSEFORGE_PUBLIC_FEED = "1"` as a top-level secret so the app reads the public feed instead of the fixed local demo seed. This is a **non-secret feature flag**, not an API key.
4. Deploy, then confirm the public app URL and that the source caption says public GitHub synthetic feed.
5. In GitHub Actions, manually run **Daily synthetic dashboard refresh** once to bootstrap `data/public/`, then verify the workflow passes and all four files appear together on `main`.

The assistant cannot authenticate to or click through the owner's Streamlit Community Cloud account using the GitHub repository connector. Deployment and GitHub repository Actions write-policy settings may require owner approval.

## M71 live customer-analytics acceptance

The published 2026-11-23 snapshot includes `latest_payments.csv` and a versioned `payment_sidecar` entry in `status.json`. This proves publication, **not** that the hosted Streamlit UI rendered it.

The app owner or an independent browser tester must check the public app at https://pulseforge-analytics.streamlit.app:

1. Confirm the app opens without an error and identifies the **public GitHub synthetic feed** rather than the bundled local seed.
2. Confirm the **Synthetic customer purchase analytics** section displays **RFM segments (gross successful orders)** and **Observed payment value (per currency)** tables, without a payment-feed warning.
3. Confirm the dashboard reports **2,669 events, 560 sessions, and 241 sessions with payment** for the unfiltered 2026-11-23 snapshot. These counts will change after the next successful daily publication; compare with the current `data/public/status.json` instead of treating these values as permanent.
4. Change the UTC date slider and verify that the dashboard remains responsive, counts change consistently, and payment analytics do not claim exact session-start-cohort filtering.
5. Confirm the last successful publication timestamp is visible, and that a missing or corrupted feed produces a warning/error rather than silently substituting the local demo seed.

Record the observed timestamp, app URL, screenshot or browser-test output, and the corresponding GitHub commit before marking live UI acceptance complete. A passing Streamlit AppTest in CI is **not** browser-level proof of the deployed app.

The public publisher now also validates payment-sidecar integrity and Bronze linkage before committing. The scheduled independent health monitor requires the payment sidecar. GitHub Actions has a scoped push trigger for publisher implementation changes, but a successful initial publication does not prove two consecutive scheduled refreshes.

## Monitoring and recovery

- The workflow is the daily operational monitor: a failing generation, dbt, integrity or publish step produces a red GitHub Actions run. GitHub Actions notifications can be enabled for failures.
- `data/public/status.json` contains the last **successful** synthetic feed's date and event/session counts. A failed job leaves the previous published commit unchanged.
- The dashboard's remote feed refuses hash mismatches; it does not silently show the bundled seed.
- No self-healing production controller, private alerting service or paid hosting is implied.
- The workflow publishes synthetic CSV to a public repository: do not substitute real personal or client data.
