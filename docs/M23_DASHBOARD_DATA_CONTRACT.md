# M23 — Dashboard-to-warehouse metric parity

This incremental milestone checks that the M21/M22 Python dashboard metrics match the actual M20 dbt DuckDB marts for the same synthetic seed. A separate GitHub Actions job builds a disposable file-backed DuckDB database under `/tmp` and compares session totals, paid-session totals, session-start cohort stage counts, daily event totals and distinct daily users.

The test is skipped in the regular pytest workflow when no disposable DuckDB path is supplied; the dedicated M23 workflow sets the path and runs it. This is **not** a production data connection or a public deployment. The dashboard continues to read the synthetic seed directly; the new test detects metric drift between two independent implementations.

No operational SQLite database is opened or modified.
