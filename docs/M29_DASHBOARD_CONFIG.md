# M29 — Configurable Streamlit demo source

The Streamlit dashboard still defaults to the checked-in synthetic Bronze CSV. To view a generated **Bronze-format CSV**, configure the `PULSEFORGE_DASHBOARD_CSV` environment variable to its path before starting Streamlit.

The source must contain `event_id,event_name,session_id,user_id,event_time`. Dashboard metrics use the same validated CSV loader and UTC session-start cohort rules. Errors are shown inside Streamlit instead of producing an unhandled file-read traceback.

This is a configuration feature, not a direct DuckDB connector or production streaming feed. M28 already tests parity against generated SQLite and dbt datasets. The dashboard has not been browser-tested in this milestone.
