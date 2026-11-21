# M28 — Generated-data dashboard metric parity

M28 extends the M27 generated-events pipeline by running the real dashboard metrics functions over the exported generated Bronze CSV, then comparing their event, session, paid-session and daily cohort metrics against both the SQLite Silver/Gold baseline and a disposable dbt DuckDB warehouse.

The test uses 30 generated customer journeys. It runs in GitHub Actions and creates only disposable data under /tmp/m28. The standard test suite skips the integration test unless M28_OUTPUT_DIR is set by CI.

**Scope:** independent metric consistency across generator → SQLite SQL views → normalized CSV → dbt warehouse → dashboard calculations.

**Not covered:** a deployed Streamlit frontend, rendered browser UI, or streaming the broker output directly into dbt. A green test should not be described as full production end-to-end validation.
