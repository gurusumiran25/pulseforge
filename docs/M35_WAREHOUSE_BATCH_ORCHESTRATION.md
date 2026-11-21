# M35 — Explicit warehouse batch orchestration

M35 packages the M32 SQLite Bronze export and dbt DuckDB build into one repeatable, **explicitly invoked** command:

`python -m services.analytics.warehouse_batch --db-path <disposable-events.db> --workspace <empty-output-directory>`

It copies the dbt project into a new workspace, exports a consistent SQLite snapshot, creates an isolated DuckDB profile, and executes `dbt build`. It never deletes or replaces a nonempty output workspace, and refuses to run if the workspace contains the source database. Fixed six-row demo assertions are excluded for generated snapshots; model/schema tests remain active.

Unit tests mock the external dbt process and verify command invocation and file safety. M33/M34 separately exercise actual dbt builds and real Redpanda broker data. This milestone does **not** introduce scheduled orchestration, incremental processing, production credentials, or a continuously updated warehouse.
