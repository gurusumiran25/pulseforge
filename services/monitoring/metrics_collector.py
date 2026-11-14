"""Read-only operational metrics for PulseForge."""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path


IST = timezone(timedelta(hours=5, minutes=30))


def _connect_readonly(path):
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(f"Database missing: {path}")

    uri = path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _database_metrics(path, table):
    with _connect_readonly(path) as connection:
        integrity = connection.execute(
            "PRAGMA quick_check"
        ).fetchone()[0]

        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

    return {
        "integrity": integrity,
        "row_count": count,
    }


def _latest_runs(log_path):
    path = Path(log_path)

    if not path.exists():
        return {}

    latest = {}

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        run_date = record.get("run_date")

        if run_date:
            latest[run_date] = record.get("status")

    return latest


def _quality_metrics(report_dir, current_events, now):
    directory = Path(report_dir)

    reports = sorted(
        directory.glob("quality_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not reports:
        return {
            "status": "UNKNOWN",
            "reason": "No quality report available",
        }

    path = reports[0]

    report = json.loads(
        path.read_text(encoding="utf-8")
    )

    generated_at = datetime.fromisoformat(
        report["generated_at_utc"].replace("Z", "+00:00")
    )

    age_hours = max(
        0.0,
        (now - generated_at).total_seconds() / 3600,
    )

    covered_events = report["total_events"]

    return {
        "status": report["status"],
        "score": report["quality_score"],
        "grade": report["quality_grade"],
        "report_path": str(path),
        "report_age_hours": round(age_hours, 2),
        "covered_events": covered_events,
        "current_events": current_events,
        "coverage_current": covered_events == current_events,
    }


def collect_metrics(
    event_db="data/automation/events.db",
    customer_db="data/automation/customers.db",
    log_path="data/automation/daily_runs.jsonl",
    report_dir="reports/quality",
    now=None,
):
    now = now or datetime.now(timezone.utc)

    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    now = now.astimezone(timezone.utc)
    today = now.astimezone(IST).date().isoformat()

    events = _database_metrics(event_db, "events")
    customers = _database_metrics(customer_db, "customers")

    with _connect_readonly(event_db) as connection:
        rows = connection.execute(
            "SELECT event_name, COUNT(*) "
            "FROM events GROUP BY event_name"
        ).fetchall()

    event_types = dict(rows)

    successful = event_types.get("payment_succeeded", 0)
    failed = event_types.get("payment_failed", 0)
    attempts = successful + failed

    runs = _latest_runs(log_path)

    quality = _quality_metrics(
        report_dir,
        events["row_count"],
        now,
    )

    return {
        "schema_version": "1.0",
        "generated_at_utc": now.isoformat(),
        "today_ist": today,
        "storage": {
            "events": events,
            "customers": customers,
        },
        "simulation": {
            "today_status": runs.get(today, "missing"),
            "completed_days": sum(
                status == "completed"
                for status in runs.values()
            ),
            "latest_runs": runs,
        },
        "data_quality": quality,
        "analytics": {
            "event_types": event_types,
            "successful_payments": successful,
            "failed_payments": failed,
            "payment_success_pct": (
                round(successful / attempts * 100, 2)
                if attempts else None
            ),
        },
    }


if __name__ == "__main__":
    print(json.dumps(collect_metrics(), indent=2))
