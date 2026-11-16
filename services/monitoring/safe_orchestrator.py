"""Fail-closed post-simulation monitoring orchestrator.

Preview-only: never simulates, repairs, or persists data.
"""

from services.monitoring.run_consistency import verify_run_consistency
from services.monitoring.metrics_collector import collect_metrics
from services.monitoring.snapshot_store import build_snapshot


def run_safe_monitoring(
    *,
    run_date,
    log_path="data/automation/daily_runs.jsonl",
    event_db="data/automation/events.db",
    customer_db="data/automation/customers.db",
    report_dir="reports/quality",
    preview=True,
    automatic_recovery_enabled=False,
):
    if preview is not True:
        raise PermissionError(
            "Monitoring persistence is not authorized"
        )

    if automatic_recovery_enabled is not False:
        raise PermissionError(
            "Automatic recovery is not authorized"
        )

    identity = verify_run_consistency(
        log_path, event_db, run_date
    )

    metrics = collect_metrics(
        event_db=event_db,
        customer_db=customer_db,
        log_path=log_path,
        report_dir=report_dir,
    )

    current_events = metrics["storage"]["events"]["row_count"]

    if current_events != identity["events_after"]:
        raise RuntimeError(
            "Monitoring metrics changed after consistency check"
        )

    snapshot = build_snapshot(metrics)

    # Revalidate immediately after metrics collection.
    verified = verify_run_consistency(
        log_path, event_db, run_date
    )

    if verified["run_id"] != identity["run_id"]:
        raise RuntimeError("Simulation run identity changed")

    if verified["events_after"] != current_events:
        raise RuntimeError("Simulation data changed during monitoring")

    return {
        "mode": "PREVIEW",
        "run_id": identity["run_id"],
        "run_date": run_date,
        "event_count": current_events,
        "overall_status": snapshot["overall_status"],
        "alert_codes": [
            alert["code"] for alert in snapshot["alerts"]
        ],
        "snapshot_persisted": False,
        "quality_report_persisted": False,
        "recovery_executed": False,
        "simulation_executed": False,
        "scheduler_modified": False,
    }
