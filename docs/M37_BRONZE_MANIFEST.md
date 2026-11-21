# M37 — Bronze snapshot integrity manifest

M37 adds a JSON sidecar with schema version, UTC creation time, row count and SHA-256 digest for an exported Bronze CSV. A verification command detects mismatched, stale, damaged or unexpectedly replaced snapshots before downstream use.

Create: `python -m services.analytics.bronze_manifest --csv <bronze.csv> --manifest <bronze.manifest.json>`

Verify: `python -m services.analytics.bronze_manifest --csv <bronze.csv> --manifest <bronze.manifest.json> --verify`

Both the snapshot and manifest must be treated as a pair. The manifest is atomically replaced after checking the CSV digest again, but this is **not an atomic two-file transaction**: concurrent writers can still race. The manifest is not cryptographically signed and is not an authorization mechanism. M37 provides integrity verification and detection, not full transactional checkpointing, distributed locking, or automatic recovery.
