# M45 — Reproducible one-command portfolio demonstration

Install the portfolio extras with `python -m pip install -e '.[dev,portfolio]'` in a fresh environment. Then execute:

```bash
python -m services.analytics.portfolio_demo --output-root /tmp/pulseforge-demo --sessions 20
```

The output root must not contain existing files. The command generates synthetic customer journeys, persists them to SQLite, exports an integrity-verified Bronze CSV, executes a **real** dbt DuckDB build, applies eight semantic quality checks, creates a run report, checks warehouse health, and reconciles event count, session count and successful-payment session count with the dashboard's pure metric calculations.

Artifacts are saved in the output directory: `events.db`, `run-report.json`, `build/dbt/seeds/bronze_events.csv`, `build/bronze.manifest.json`, `build/warehouse.duckdb`, and `demo-summary.json`.

The dedicated M45 GitHub Actions workflow runs the demonstration against a fresh Python 3.12 environment with real dbt and DuckDB. The **real Redpanda broker integration** is separately verified by the existing M33/M34 workflows. This demo is an isolated, synthetic, one-shot acceptance test; it does not launch Kafka, FastAPI, or Streamlit servers and is not a deployed production pipeline.
