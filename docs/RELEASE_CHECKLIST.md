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

## Scope boundary

The target is a **reproducible portfolio demonstration** using synthetic data, not an always-on production service. Airflow, distributed storage, continuous cloud deployment and operational SLAs are not required to declare the portfolio release complete. They remain optional follow-on engineering work.

Do not mark any checkbox complete solely because a source file exists. Verify each acceptance criterion against CI or a documented test run.
