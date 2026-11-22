# M39 — Warehouse run reporting and diagnostics

M39 wraps the explicit M38 warehouse batch with a JSON report containing a unique run ID, UTC start/end timestamps, duration, outcome and either the resulting warehouse path/export count or exception type/message. The report is written atomically to a caller-selected path **outside** the isolated build workspace, so a failed build can still leave a diagnostic record.

Usage:

`python -m services.analytics.warehouse_run_report --db-path <events.db> --workspace <new-empty-workspace> --report <separate-report.json>`

Failure reports preserve the original exception after saving the report. Reports may contain file paths and exception messages, so treat them as operational artifacts and review before publishing. The reporting layer does not provide metrics collection, tracing, alerting, automatic retries, a scheduler, or a persistent monitoring service. CI tests mock the warehouse batch to test reporting independently.
