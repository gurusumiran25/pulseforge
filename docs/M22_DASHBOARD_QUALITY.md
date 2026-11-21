# M22 — Dashboard quality and cohort correctness

This incremental dashboard quality milestone corrects an M21 ambiguity: event-date filtering could cut off a cross-midnight session, altering session-start cohort dates and observed payment flags. M22 selects sessions by the UTC date of their **first event** and includes every event from those sessions.

The date range is inclusive. Daily event activity can legitimately show dates outside the selected cohort range because selected sessions can span midnight. This is expected, not a bug.

## Verification

`tests/dashboard/test_m22_cohort_filter.py` asserts that a Nov 19 cohort retains its Nov 20 payment, that the Nov 20 cohort excludes the earlier session, and that invalid ranges are rejected. The existing standard pytest and M21 dashboard workflows cover these tests on the M22 branch.

This is still a synthetic demonstration dataset; no operational data is accessed.
