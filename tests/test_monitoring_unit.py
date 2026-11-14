"""Isolated unit tests for PulseForge monitoring."""

import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.monitoring.quality_monitor import evaluate_quality
from services.monitoring.alert_engine import evaluate_alerts
from services.monitoring.snapshot_store import (
    build_snapshot,
    save_snapshot,
    get_latest_snapshot,
)


def sample_metrics():
    return {
        "schema_version": "1.0",
        "generated_at_utc": "2026-11-14T08:00:00+00:00",
        "storage": {
            "events": {"integrity": "ok", "row_count": 100},
            "customers": {"integrity": "ok", "row_count": 20},
        },
        "data_quality": {
            "status": "PASS",
            "score": 100.0,
            "grade": "EXCELLENT",
            "report_age_hours": 1.0,
            "coverage_current": True,
        },
    }


class QualityMonitorTests(unittest.TestCase):

    def setUp(self):
        self.metrics = sample_metrics()

    def test_healthy_quality(self):
        result = evaluate_quality(self.metrics)
        self.assertEqual(result["status"], "HEALTHY")

    def test_outdated_coverage(self):
        self.metrics["data_quality"]["coverage_current"] = False
        result = evaluate_quality(self.metrics)
        self.assertEqual(result["status"], "DEGRADED")

    def test_warning_freshness(self):
        self.metrics["data_quality"]["report_age_hours"] = 25
        result = evaluate_quality(self.metrics)
        self.assertEqual(result["status"], "DEGRADED")

    def test_critical_quality_score(self):
        self.metrics["data_quality"]["score"] = 60
        self.metrics["data_quality"]["grade"] = "CRITICAL"
        result = evaluate_quality(self.metrics)
        self.assertEqual(result["status"], "CRITICAL")

    def test_failed_database_integrity(self):
        self.metrics["storage"]["events"]["integrity"] = "corrupt"
        result = evaluate_quality(self.metrics)
        self.assertEqual(result["status"], "CRITICAL")

    def test_missing_quality_report(self):
        self.metrics["data_quality"] = {
            "status": "UNKNOWN",
            "reason": "No report available",
        }
        result = evaluate_quality(self.metrics)
        self.assertEqual(result["status"], "UNKNOWN")

    def test_invalid_thresholds(self):
        with self.assertRaises(ValueError):
            evaluate_quality(
                self.metrics,
                warning_hours=48,
                critical_hours=24,
            )


class AlertEngineTests(unittest.TestCase):

    def test_no_alerts_when_healthy(self):
        self.assertEqual(evaluate_alerts(sample_metrics()), [])

    def test_outdated_report_alert(self):
        metrics = sample_metrics()
        metrics["data_quality"]["coverage_current"] = False

        alerts = evaluate_alerts(metrics)

        self.assertEqual(len(alerts), 1)
        self.assertEqual(
            alerts[0]["code"],
            "QUALITY_REPORT_OUTDATED",
        )

    def test_critical_database_alert(self):
        metrics = sample_metrics()
        metrics["storage"]["events"]["integrity"] = "failed"

        codes = {
            alert["code"]
            for alert in evaluate_alerts(metrics)
        }

        self.assertIn("EVENTS_DB_INTEGRITY_FAILURE", codes)
        self.assertIn("QUALITY_CRITICAL", codes)

    def test_deterministic_alert_id(self):
        metrics = sample_metrics()
        metrics["data_quality"]["coverage_current"] = False

        first = evaluate_alerts(metrics)
        second = evaluate_alerts(copy.deepcopy(metrics))

        self.assertEqual(first, second)


class SnapshotTests(unittest.TestCase):

    def test_snapshot_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "monitoring.db"

            snapshot = build_snapshot(sample_metrics())
            snapshot_id = save_snapshot(snapshot, db_path=db)
            restored = get_latest_snapshot(db_path=db)

            self.assertEqual(restored["snapshot_id"], snapshot_id)
            self.assertEqual(restored["overall_status"], "HEALTHY")

    def test_missing_snapshot_database(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "missing.db"
            self.assertIsNone(get_latest_snapshot(db_path=db))


class MonitoringApiTests(unittest.TestCase):

    def setUp(self):
        try:
            from fastapi.testclient import TestClient
            from services.monitoring.api import app
        except ImportError as exc:
            self.fail(f"HTTP test dependency unavailable: {exc}")

        self.client = TestClient(app)
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

        self.db = Path(self.tempdir.name) / "monitoring.db"

        snapshot = build_snapshot(sample_metrics())
        save_snapshot(snapshot, db_path=self.db)

        self.patch_db = patch(
            "services.monitoring.api.DEFAULT_DB",
            str(self.db),
        )
        self.patch_snapshot_db = patch(
            "services.monitoring.snapshot_store.DEFAULT_DB",
            str(self.db),
        )

        self.patch_db.start()
        self.patch_snapshot_db.start()

        self.addCleanup(self.patch_db.stop)
        self.addCleanup(self.patch_snapshot_db.stop)

    def test_http_health(self):
        response = self.client.get("/monitoring/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "available")

    def test_http_latest(self):
        response = self.client.get("/monitoring/latest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["overall_status"],
            "HEALTHY",
        )

    def test_http_history(self):
        response = self.client.get(
            "/monitoring/history",
            params={"limit": 10},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_http_invalid_limit(self):
        response = self.client.get(
            "/monitoring/history",
            params={"limit": 101},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main(verbosity=2)
