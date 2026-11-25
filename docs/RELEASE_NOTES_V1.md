# PulseForge v1.0.0 — draft release notes

**Unreleased.** Publish only after the [release checklist](RELEASE_CHECKLIST.md) is satisfied for the exact candidate commit.

## Highlights

- Eight versioned synthetic e-commerce event types, validated FastAPI ingestion and delivery-confirmed Kafka-compatible publishing.
- Redpanda consumer with explicit offset handling, dead-letter routing and SQLite event-ID deduplication.
- Verified Bronze exports, dbt DuckDB Silver/Gold transformations and semantic quality gates.
- Session funnels, currency-separated payments and refunds, RFM customer segmentation and Streamlit analytics.
- Daily synthetic feed publication, independent freshness/integrity monitoring and bounded remote-feed retries.
- Preview-only recovery controls and reproducible isolated portfolio demo.

## Try the project

See the [README](../README.md) for isolated setup. With Python 3.12 in a fresh virtual environment, install `python -m pip install -e ".[dev,portfolio]"` and run `python -m pip check` and `python -m pytest`. Use a new empty output directory for `python -m services.analytics.portfolio_demo --output-root ./portfolio-demo-output --sessions 20`. This runs the warehouse demonstration without a live broker.

[Public dashboard](https://pulseforge-analytics.streamlit.app/) may sleep on free hosting. See [deployment instructions](M53_STREAMLIT_CLOUD.md).

## Known limitations

All data is synthetic. Batch publication is not atomic at the broker boundary; retries can duplicate messages. The public batch pipeline is separate from live streaming, and Streamlit reads verified CSV rather than DuckDB directly. Free hosting and scheduled Actions do not provide an uptime SLA. Recovery is preview-only; no production self-healing or continuously deployed broker is claimed. Python 3.12 is the CI baseline; broader Python compatibility is not certified by that baseline alone.

## Release evidence — pending

Record the exact candidate SHA, clean-install and dependency checks, real broker and dbt runs, hosted Chromium screenshot, consecutive scheduled feed and monitor runs, and tracked-content/history security review before publication. Do not mark any gate complete based solely on this draft. Package version and tag must agree at publication.
