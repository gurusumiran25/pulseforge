# M34 — Broker-backed dashboard KPI parity

M34 extends the M33 dedicated real-Redpanda integration test to run the **same pure KPI calculations used by Streamlit** over the Bronze CSV snapshot exported from the real Kafka consumer's SQLite database. It asserts event count, sessions, paid sessions and UTC daily cohort stage flags agree with SQLite Gold SQL and dbt DuckDB marts.

The test still uses isolated CI Redpanda topics and disposable local storage. It is **not** a browser rendering test, continuously updated warehouse, or deployed system. The actual Streamlit script and widgets are separately tested by M31.
