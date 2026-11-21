# M31 — Streamlit rendered-widget integration tests

The M21 workflow checks syntax, dashboard calculations and Streamlit's HTTP health endpoint, but the health endpoint does not prove that the app script renders correctly.

M31 uses Streamlit's supported `streamlit.testing.v1.AppTest` harness to execute the actual dashboard script and inspect KPI widgets. It verifies the default synthetic dataset, an explicitly configured generated Bronze-format CSV containing a midnight-crossing session, and a missing-source error message.

**Scope:** Streamlit script execution and widget state inside an automated test harness. This is stronger than a server health check but **not** a real browser screenshot, visual regression, or production deployment test.
