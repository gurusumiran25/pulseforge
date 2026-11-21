# M36 — Idempotent Bronze snapshot refresh

M36 adds a repeatable snapshot refresh for successive ingestion batches. The existing Bronze CSV acts as the checkpoint by its set of event IDs. Each run validates that existing exported rows still match SQLite, then atomically replaces the CSV with all committed events and reports the number of newly added IDs.

The refresh **scans all SQLite events and rewrites the complete CSV**. It is incremental in logical *new-event detection*, not an optimized incremental database scan, append-only writer, or streaming warehouse. A future milestone can add transactional watermark storage, concurrency protection, and scalable partitioned exports.

This is explicit invocation, not a scheduler. Tests cover repeat runs, later batches, duplicate protection, invalid prior snapshots and missing databases.
