# Native Power BI acceptance

Source CI and TOM deserialization are prerequisites, not runtime certification.

## Candidate preparation
- Record exact commit SHA and download its pulseforge-pbip-candidate artifact.
- Obtain a published immutable BI snapshot ID and verify its manifest, freshness and nine tables.
- Generate the package with `python -m services.analytics.bi_pbip build/PulseForge --snapshot-id <64-character-id>` or configure the SnapshotId parameter in Desktop.
- Open PulseForge.pbip in supported Power BI Desktop; record version and refresh all tables.

## Runtime acceptance
- Confirm ten model tables, twelve relationships and 34 measures.
- Compare events, sessions, paid sessions, conversion, successful/failed payments and failure rate against the Python reference for the identical snapshot and date context.
- Compare gross, refunds and net per currency; verify mixed currency totals are blank.
- Check customer RFM, immature cohort blanks and prior-window/rolling metrics against reference calculations.
- Verify all seven pages, 41 visual definitions, theme, navigation, drillthrough and growth colors. Correct unsupported visual roles or formatting before certification.
- Capture one screenshot per page and record actual versus expected values, snapshot ID, commit, Desktop version and result. Do not include credentials.

## Service acceptance
- Publish only to an authorized workspace. Configure credentials and licensing as required.
- Update the immutable SnapshotId before triggering a serialized refresh; do not overlap refreshes.
- Verify successful refresh history and report values against the published snapshot.
- On failure restore last-good parameter and refresh; record incident.

## Release
Do not certify v1.1.0 until runtime evidence and final exact-SHA CI are available. Service refresh may be excluded only with explicit owner approval and clear release notes. Preserve v1.0.0 tag.
