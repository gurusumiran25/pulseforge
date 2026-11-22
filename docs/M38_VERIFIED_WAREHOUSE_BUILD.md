# M38 — Verified Bronze warehouse build

The explicit M35 warehouse batch command now creates an M37 SHA-256 and row-count manifest for its Bronze snapshot and verifies that manifest before invoking dbt. An integrity failure blocks the downstream dbt build.

The manifest is stored in the isolated output workspace, alongside the copied dbt project and DuckDB file. M38 tests validate manifest generation and fail-closed behavior with the dbt subprocess mocked.

**Limitations:** This is a snapshot integrity gate, not an atomic multi-file transaction or cryptographic signature. The CSV can still change after verification if another process writes to the workspace; the workflow assumes a single writer and a private output directory. Existing M33/M34 CI covers actual dbt builds separately.
