# M51 — Immutable incremental Bronze chunk publication

The original `incremental_bronze.refresh_bronze` rebuilds the complete CSV from SQLite and remains supported. The new `immutable_bronze_chunks.publish_chunk` offers a separate, **actual incremental SQLite query** using `rowid > after_rowid`, with an index-backed rowid scan rather than rereading the full events table.

For each call, the module reads a consistent SQLite snapshot, writes a CSV, verifies a SHA-256/row-count manifest, and writes a JSON checkpoint **inside a private staging directory**. It then publishes the complete directory using a same-filesystem rename. Readers should only consume published directories, never temporary directories. This avoids a visible half-written CSV/manifest pair for this new workflow.

Callers pass the last successful `next_rowid` as `after_rowid` on the next invocation. Snapshot names default to `after-<watermark>`, and existing snapshots are not overwritten. This API is opt-in and does not change the existing one-shot dbt warehouse builder.

**Boundaries:** This is an append-only, single-publisher protocol. Deleting or rewriting SQLite events, concurrent publishers using the same destination name, distributed filesystems, and integrating multiple chunks into dbt are not covered. Do not claim this makes the original CSV+manifest pair a two-file atomic transaction.
