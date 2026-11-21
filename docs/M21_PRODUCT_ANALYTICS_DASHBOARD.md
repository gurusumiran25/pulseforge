# M21 — Product Analytics Dashboard

## Initial scope
A recruiter-facing Streamlit interface reading the existing M20 **synthetic** Bronze CSV. It displays event, session, user and paid-session KPIs; session-stage participation; session-start cohorts; daily activity; and session drill-down.

## Metric contracts
- A **session** is a distinct `session_id` in the filtered dataset.
- A **paid session** has at least one `payment_succeeded` event.
- Stage participation is **not** chronological funnel conversion.
- A session's cohort date is the UTC date of its first *observed* event.
- Daily activity counts events and distinct users by UTC event date.
- Date filtering is event-based, so a partial session can change its observed first date or stage flags.
- The synthetic seed has only six events; these numbers are not business performance benchmarks.

## Architecture and verification
- `apps/dashboard/metrics.py` uses only Python's standard library and reads the M20 CSV.
- `apps/dashboard/streamlit_app.py` is the optional Streamlit presentation layer.
- `tests/dashboard/test_m21_metrics.py` checks the expected seed metrics, empty filters, duplicate IDs, and independent stage flags.
- Standard GitHub Actions pytest executes the metric tests. A dedicated Streamlit smoke test can be added before merging.

## Local deployment (optional)
Install `streamlit>=1.39,<2` and run `streamlit run apps/dashboard/streamlit_app.py` from the repository root. No terminal work is required for repository CI. This milestone does not deploy a public hosted dashboard or connect to operational databases.
