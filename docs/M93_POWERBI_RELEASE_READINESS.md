# M93 — Power BI integration release readiness

Status: reference implementation validated; native Power BI acceptance pending.

## Verified evidence

At commit 8d7f73a65b92830b66c229d50fc4461e9af42a1f:
- [M92 combined acceptance](https://github.com/gurusumiran25/pulseforge/actions/runs/46142095867) — success.
- [M92 second trigger](https://github.com/gurusumiran25/pulseforge/actions/runs/46142094135) — success.
- [M53 real daily feed](https://github.com/gurusumiran25/pulseforge/actions/runs/46142095885) — success.

These checks exercise Python reference calculations, real dbt processing, snapshot integrity, relationships and static report/navigation contracts. They do not execute DAX or Power Query in Microsoft Power BI.

## Desktop handoff

1. After approved publication of the BI feed, obtain the snapshot ID from data/bi/current.json on main. Verify its manifest and freshness before use.
2. In Power BI Desktop create a text parameter SnapshotId with that immutable ID. Import the nine tables using powerbi/queries/LoadSnapshotTable.pq and TABLES.md.
3. Configure relationships from powerbi/model/schema.json and the calendar and disconnected cohort definitions from the measure documentation.
4. Add the DAX measures from docs/M88_POWERBI_DAX.md and powerbi/measures. Build the seven pages using powerbi/report/report_spec.json and navigation_layout.json.
5. Compare native results with reference calculations for a pinned snapshot, including single/multiple currency, empty filters and immature cohorts. Exercise navigation and drillthrough. Capture actual screenshots and record Desktop version and snapshot ID.

## Service refresh handoff

The existing daily publisher is scheduled for 02:30 UTC. The feature branch does not itself activate the main-branch publication schedule. After publication, verify the new snapshot, update the dataset parameter to its immutable ID, then refresh and verify completion before advancing the recorded last-good snapshot. Serialize parameter changes and refreshes. A time-only refresh schedule does not update the pinned parameter automatically.

Service authentication, workspace permissions, licensing and API availability must be confirmed by the owner. No credentials belong in Git. No public sharing is required. A failed verification must prevent refresh; a failed refresh requires investigation and restoration of the last-good parameter where necessary.

## Release gates

- [x] M92 reference acceptance and M53 real warehouse tests green at evidence SHA.
- [ ] Native Desktop report saved and opened successfully.
- [ ] Native DAX and Power Query parity verified.
- [ ] Actual report screenshots and interaction evidence captured.
- [ ] Main-branch BI publication and hosted snapshot verified.
- [ ] Service refresh configured and observed, or explicitly excluded from release scope by owner.
- [ ] Final exact-candidate CI and security checks green.
- [ ] Approved release published.

Keep v1.0.0 immutable. Do not describe this branch as a deployed Power BI dashboard or publish a full Power BI release before native acceptance.
