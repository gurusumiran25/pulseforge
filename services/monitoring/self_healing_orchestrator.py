"""Fail-closed, preview-only self-healing orchestration."""

from services.monitoring.run_consistency import verify_run_consistency
from services.monitoring.metrics_collector import collect_metrics
from services.monitoring.snapshot_store import build_snapshot
from services.monitoring.recovery_policy import evaluate_recovery


def plan_self_healing(
    *,
    run_date,
    log_path="data/automation/daily_runs.jsonl",
    event_db="data/automation/events.db",
    customer_db="data/automation/customers.db",
    report_dir="reports/quality",
    preview=True,
    automatic_recovery_enabled=False,
    persist=False,
):
    if preview is not True:
        raise PermissionError("Execution mode is not authorized")

    if automatic_recovery_enabled is not False:
        raise PermissionError("Automatic recovery is not authorized")

    if persist is not False:
        raise PermissionError("Monitoring persistence is not authorized")

    identity = verify_run_consistency(
        log_path, event_db, run_date
    )

    metrics = collect_metrics(
        event_db=event_db,
        customer_db=customer_db,
        log_path=log_path,
        report_dir=report_dir,
    )

    event_count = metrics["storage"]["events"]["row_count"]

    if event_count != identity["events_after"]:
        raise RuntimeError(
            "Event count changed during monitoring"
        )

    snapshot = build_snapshot(metrics)

    verified = verify_run_consistency(
        log_path, event_db, run_date
    )

    if (
        verified["run_id"] != identity["run_id"]
        or verified["events_after"] != event_count
        or verified["database_events"] != event_count
        or verified["consistent"] is not True
    ):
        raise RuntimeError(
            "Simulation consistency changed during monitoring"
        )

    alerts = [alert["code"] for alert in snapshot["alerts"]]

    decisions = [
        evaluate_recovery(
            alert_code=code,
            automatic_recovery_enabled=False,
        )
        for code in alerts
    ]

    return {
        "mode": "PREVIEW",
        "run_id": identity["run_id"],
        "run_date": run_date,
        "event_count": event_count,
        "overall_status": snapshot["overall_status"],
        "alert_codes": alerts,
        "recovery_decisions": decisions,
        "recovery_executed": False,
        "quality_report_persisted": False,
        "snapshot_persisted": False,
        "simulation_executed": False,
        "scheduler_modified": False,
    }
