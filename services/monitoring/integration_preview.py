"""Safe end-to-end monitoring storage preview for PulseForge M18."""

import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from services.monitoring.metrics_collector import collect_metrics
from services.monitoring.snapshot_store import (
    build_snapshot,
    get_latest_snapshot,
)
from services.monitoring.compatible_store import save_compatible_once
from services.monitoring.quality_refresh import refresh_quality


def run_integration_preview():
    quality = refresh_quality(execute=False)

    metrics = collect_metrics()
    snapshot = build_snapshot(metrics)

    with tempfile.TemporaryDirectory() as directory:
        db = Path(directory) / "monitoring.db"

        first_id, first_created = save_compatible_once(
            snapshot,
            "m18-stage10f-test",
            db,
        )

        duplicate_id, duplicate_created = save_compatible_once(
            snapshot,
            "m18-stage10f-test",
            db,
        )

        assert first_created is True
        assert duplicate_created is False
        assert first_id == duplicate_id

        restored = get_latest_snapshot(db_path=db)

        assert restored is not None
        assert restored["snapshot_id"] == first_id
        assert restored["overall_status"] == snapshot["overall_status"]
        assert restored["metrics"] == snapshot["metrics"]

        with closing(sqlite3.connect(db)) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM monitoring_snapshots"
            ).fetchone()[0]

            registry_count = conn.execute(
                "SELECT COUNT(*) FROM monitoring_run_registry"
            ).fetchone()[0]

            integrity = conn.execute(
                "PRAGMA quick_check"
            ).fetchone()[0]

        assert count == 1
        assert registry_count == 1
        assert integrity == "ok"

        result = {
            "mode": "ISOLATED_INTEGRATION_PREVIEW",
            "quality_preview_status": quality["status"],
            "quality_preview_score": quality["quality_score"],
            "monitoring_status": snapshot["overall_status"],
            "assessment_scope": snapshot["assessment_scope"],
            "events": metrics["storage"]["events"]["row_count"],
            "customers": metrics["storage"]["customers"]["row_count"],
            "alerts": len(snapshot["alerts"]),
            "temporary_snapshot_created": first_created,
            "duplicate_prevented": not duplicate_created,
            "m17_reader_compatible": True,
            "temporary_database_integrity": integrity,
            "production_snapshot_persisted": False,
            "simulation_executed": False,
            "scheduler_modified": False,
        }

    return result


if __name__ == "__main__":
    print(json.dumps(run_integration_preview(), indent=2))
