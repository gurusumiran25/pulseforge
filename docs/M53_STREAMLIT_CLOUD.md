# M53 — Scheduled synthetic feed + Streamlit Community Cloud

## Architecture

GitHub Actions runs the daily publisher at **02:30 UTC (08:00 IST)**, with a manual `workflow_dispatch` option. The run generates a fresh **rolling 14-day** synthetic dataset (40 sessions/day), inserts into a disposable SQLite database, executes real dbt DuckDB marts, verifies the eight semantic checks and warehouse health, reconciles dashboard counts, then commits **CSV + SHA-256 manifest + status JSON together** to `data/public/` in one Git commit. No operational database, credentials or customer data is published.

The Streamlit Community Cloud app uses the fixed public raw GitHub URL and verifies CSV SHA-256 and row count against the manifest. Its cache expires every **3600 seconds**, so an already-running app can fetch a newer feed on its next rerun after expiry. GitHub Actions scheduled jobs may be delayed or disabled; there is **no guarantee of a refresh at exactly 08:00 IST**. GitHub raw CDN cache propagation may briefly produce a mismatch, which fails closed instead of displaying unverified data.

## Deploy Streamlit Community Cloud (account owner action)

1. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with the GitHub account authorized for `gurusumiran25/pulseforge`.
2. Select the repository, branch `main`, entry point `apps/dashboard/streamlit_app.py`. Set Python 3.12 if offered. The repository's `requirements.txt` or equivalent installation configuration must be recognized by the deployment.
3. In the app's advanced settings / secrets, add `PULSEFORGE_PUBLIC_FEED = "1"` as a top-level secret so the app reads the public feed instead of the fixed local demo seed. This is a **non-secret feature flag**, not an API key.
4. Deploy, then confirm the public app URL and that the source caption says public GitHub synthetic feed.
5. In GitHub Actions, manually run **Daily synthetic dashboard refresh** once to bootstrap `data/public/`, then verify the workflow passes and the three files appear together on `main`.

The assistant cannot authenticate to or click through the owner's Streamlit Community Cloud account using the GitHub repository connector. Deployment and GitHub repository Actions write-policy settings may require owner approval.

## Monitoring and recovery

- The workflow is the daily operational monitor: a failing generation, dbt, integrity or publish step produces a red GitHub Actions run. GitHub Actions notifications can be enabled for failures.
- `data/public/status.json` contains the last **successful** synthetic feed's date and event/session counts. A failed job leaves the previous published commit unchanged.
- The dashboard's remote feed refuses hash mismatches; it does not silently show the bundled seed.
- No self-healing production controller, private alerting service or paid hosting is implied.
- The workflow publishes synthetic CSV to a public repository: do not substitute real personal or client data.
