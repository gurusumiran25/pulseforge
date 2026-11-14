"""Persist PulseForge monitoring snapshots separately from source data."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from services.monitoring.metrics_collector import collect_metrics
from services.monitoring.quality_monitor import evaluate_quality
from services.monitoring.alert_engine import evaluate_alerts


DEFAULT_DB = "data/monitoring/monitoring.db"


def build_snapshot(metrics):
    quality = evaluate_quality(metrics)
    alerts = evaluate_alerts(metrics)

    storage = metrics.get("storage", {})

    storage_healthy = all(
        storage.get(name, {}).get("integrity") == "ok"
        for name in ("events", "customers")
    )

    if not storage_healthy or quality["status"] == "CRITICAL":
        overall = "CRITICAL"
    elif quality["status"] == "UNKNOWN":
        overall = "UNKNOWN"
    elif quality["status"] == "DEGRADED":
        overall = "DEGRADED"
    else:
        overall = "HEALTHY"

    # This status summarizes currently assessed components only.
    # Ingestion and other unassessed services are not implied healthy.
    return {
        "schema_version": "1.0",
        "generated_at_utc": metrics["generated_at_utc"],
        "overall_status": overall,
        "assessment_scope": ["storage", "data_quality"],
        "quality_assessment": quality,
        "metrics": metrics,
        "alerts": alerts,
    }


def save_snapshot(snapshot, db_path=DEFAULT_DB):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(
        snapshot,
        sort_keys=True,
        allow_nan=False,
    )

    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generated_at_utc TEXT NOT NULL,
                    overall_status TEXT NOT NULL,
                    alert_count INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
            """)

            cursor = connection.execute(
                """
                INSERT INTO monitoring_snapshots (
                    generated_at_utc,
                    overall_status,
                    alert_count,
                    snapshot_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    snapshot["generated_at_utc"],
                    snapshot["overall_status"],
                    len(snapshot["alerts"]),
                    payload,
                ),
            )

            return cursor.lastrowid

def get_latest_snapshot(db_path=DEFAULT_DB):
    path = Path(db_path)

    if not path.exists():
        return None

    uri = path.resolve().as_uri() + "?mode=ro"

    with closing(sqlite3.connect(uri, uri=True)) as connection:
        row = connection.execute(
            """
            SELECT id, snapshot_json
            FROM monitoring_snapshots
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

    if row is None:
        return None

    snapshot = json.loads(row[1])
    snapshot["snapshot_id"] = row[0]

    return snapshot


if __name__ == "__main__":
    metrics = collect_metrics()
    snapshot = build_snapshot(metrics)

    snapshot_id = save_snapshot(snapshot)
    restored = get_latest_snapshot()

    if restored is None or restored["snapshot_id"] != snapshot_id:
        raise RuntimeError("Snapshot verification failed")

    print(json.dumps({
        "snapshot_id": snapshot_id,
        "database": DEFAULT_DB,
        "overall_status": restored["overall_status"],
        "assessment_scope": restored["assessment_scope"],
        "event_count": restored["metrics"]["storage"]["events"]["row_count"],
        "alert_count": len(restored["alerts"]),
        "alert_codes": [
            alert["code"] for alert in restored["alerts"]
        ],
        "verification": "PASS",
    }, indent=2))
