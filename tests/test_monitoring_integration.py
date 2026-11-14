"""Failure and integration tests using isolated temporary data."""

import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from services.monitoring.api import app
from services.monitoring.metrics_collector import _connect_readonly
from services.monitoring.quality_monitor import evaluate_quality
from services.monitoring.alert_engine import evaluate_alerts
from services.monitoring.snapshot_store import (
    build_snapshot,
    save_snapshot,
    get_latest_snapshot,
)
from tests.test_monitoring_unit import sample_metrics


class FailureScenarioTests(unittest.TestCase):

    def test_missing_source_database(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.db"

            with self.assertRaises(FileNotFoundError):
                _connect_readonly(missing)

            self.assertFalse(missing.exists())

    def test_missing_quality_report(self):
        metrics = sample_metrics()
        metrics["data_quality"] = {
            "status": "UNKNOWN",
            "reason": "No quality report available",
        }

        self.assertEqual(
            evaluate_quality(metrics)["status"],
            "UNKNOWN",
        )

        codes = {
            alert["code"]
            for alert in evaluate_alerts(metrics)
        }

        self.assertIn("QUALITY_REPORT_MISSING", codes)

    def test_stale_quality_coverage(self):
        metrics = sample_metrics()
        metrics["data_quality"]["coverage_current"] = False

        snapshot = build_snapshot(metrics)

        self.assertEqual(snapshot["overall_status"], "DEGRADED")
        self.assertIn(
            "QUALITY_REPORT_OUTDATED",
            {a["code"] for a in snapshot["alerts"]},
        )

    def test_critical_integrity_failure(self):
        metrics = sample_metrics()
        metrics["storage"]["events"]["integrity"] = "corrupt"

        snapshot = build_snapshot(metrics)

        self.assertEqual(snapshot["overall_status"], "CRITICAL")
        self.assertIn(
            "EVENTS_DB_INTEGRITY_FAILURE",
            {a["code"] for a in snapshot["alerts"]},
        )

    def test_snapshot_history_order(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "history.db"

            healthy = build_snapshot(sample_metrics())

            degraded_metrics = copy.deepcopy(sample_metrics())
            degraded_metrics["data_quality"]["coverage_current"] = False
            degraded = build_snapshot(degraded_metrics)

            first_id = save_snapshot(healthy, db_path=db)
            second_id = save_snapshot(degraded, db_path=db)

            self.assertGreater(second_id, first_id)

            latest = get_latest_snapshot(db_path=db)

            self.assertEqual(latest["snapshot_id"], second_id)
            self.assertEqual(latest["overall_status"], "DEGRADED")


class MonitoringHttpFailureTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        self.db = Path(self.tempdir.name) / "monitoring.db"

        self.patcher = patch(
            "services.monitoring.api.DEFAULT_DB",
            str(self.db),
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

        self.client = TestClient(app)

    def test_health_missing_database_returns_503(self):
        response = self.client.get("/monitoring/health")

        self.assertEqual(response.status_code, 503)
        self.assertFalse(self.db.exists())

    def test_latest_missing_database_returns_404(self):
        response = self.client.get("/monitoring/latest")

        self.assertEqual(response.status_code, 404)

    def test_history_missing_database_returns_503(self):
        response = self.client.get("/monitoring/history")

        self.assertEqual(response.status_code, 503)

    def test_corrupt_database_returns_503(self):
        self.db.write_bytes(b"not a valid sqlite database")

        health = self.client.get("/monitoring/health")
        history = self.client.get("/monitoring/history")
        latest = self.client.get("/monitoring/latest")

        self.assertEqual(health.status_code, 503)
        self.assertEqual(history.status_code, 503)
        self.assertEqual(latest.status_code, 503)

    def test_empty_database_latest_returns_404(self):
        with sqlite3.connect(self.db) as connection:
            connection.execute("""
                CREATE TABLE monitoring_snapshots (
                    id INTEGER PRIMARY KEY,
                    generated_at_utc TEXT NOT NULL,
                    overall_status TEXT NOT NULL,
                    alert_count INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
            """)

        response = self.client.get("/monitoring/latest")

        self.assertEqual(response.status_code, 404)

    def test_http_history_reads_temporary_snapshots(self):
        save_snapshot(
            build_snapshot(sample_metrics()),
            db_path=self.db,
        )

        response = self.client.get(
            "/monitoring/history",
            params={"limit": 10},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["snapshots"][0]["overall_status"],
            "HEALTHY",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
