# M44 — Reproducible portfolio setup

The Python project now exposes explicit optional dependency groups:

- `pip install -e '.[dev]'` — core tests and developer tools
- `pip install -e '.[dashboard]'` — Streamlit application
- `pip install -e '.[warehouse]'` — dbt DuckDB and DuckDB client
- `pip install -e '.[dev,portfolio]'` — combined release-verification environment

The M44 workflow installs the combined environment on a clean Ubuntu Python 3.12 runner, checks dependency consistency, executes Streamlit AppTest, and executes the real quality-gated warehouse build. The broker-backed integration remains covered by a separate GitHub Actions workflow.

These are version *ranges*, not a fully locked environment; an immutable lockfile and containerized full-stack demo may be added in a later release-hardening milestone.
