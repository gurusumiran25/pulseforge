# M27 — Generated events to dbt warehouse parity

This CI milestone generates 30 synthetic customer journeys with the actual generator, persists validated envelopes in a disposable SQLite database, applies the M20 Silver/Gold SQL views, and exports a normalized Bronze CSV. A **copy** of the M20 dbt project then builds a disposable file-backed DuckDB warehouse from that generated CSV. The parity test compares event counts, session counts, paid-session counts and daily session-start cohort stage metrics across the SQLite and dbt implementations.

This is stronger than comparing two implementations on the fixed six-row demo seed, but it is still a **batch handoff**, not direct Kafka-to-dbt streaming. No production data, local working tree, or persistent operational database is modified.

The original M20 dbt project and synthetic seed remain unchanged. CI status must be verified before merge.
