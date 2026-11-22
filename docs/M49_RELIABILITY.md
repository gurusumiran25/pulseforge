# M49 reliability and retry classification

The warehouse retry policy now retries only subprocess timeouts. A nonzero dbt exit code can indicate invalid SQL, failing data tests or broken configuration; these deterministic failures are not retried. Input validation, manifest integrity and semantic quality failures also fail immediately.

Regression tests cover classification, a single attempt on a deterministic dbt failure, and the maximum three isolated attempts on a simulated timeout.

**Limitations:** subprocess timeouts can also arise from repeatable problems; retrying does not guarantee recovery. This change does not claim transactional atomicity across the Bronze CSV and its manifest. The isolated one-shot batch uses a unique empty workspace and validates the manifest before and after export. A true shared multi-writer snapshot publication protocol is a separate concern.
