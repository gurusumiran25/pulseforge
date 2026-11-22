"""M41 read-only warehouse health checks."""
import json
from unittest.mock import patch

from services.analytics.warehouse_health import check_warehouse


def test_failed_report_is_unhealthy(tmp_path):
    report = tmp_path / "failed.json"
    report.write_text(json.dumps({"schema_version": 1, "status": "failure"}), encoding="utf-8")
    result = check_warehouse(report)
    assert result["healthy"] is False
    assert any("successful" in issue for issue in result["issues"])


def test_missing_warehouse_is_unhealthy(tmp_path):
    report = tmp_path / "run.json"
    report.write_text(json.dumps({
        "schema_version": 1, "status": "success",
        "result": {
            "warehouse": str(tmp_path / "missing.duckdb"),
            "manifest": str(tmp_path / "manifest.json"),
            "events_exported": 10,
        },
    }), encoding="utf-8")
    result = check_warehouse(report)
    assert result["healthy"] is False
    assert any("missing" in issue.lower() for issue in result["issues"])


def test_reported_row_count_mismatch_is_unhealthy(tmp_path):
    report = tmp_path / "run.json"
    report.write_text(json.dumps({
        "schema_version": 1, "status": "success",
        "result": {
            "warehouse": str(tmp_path / "missing.duckdb"),
            "manifest": str(tmp_path / "manifest.json"),
            "events_exported": 10,
        },
    }), encoding="utf-8")
    with patch("services.analytics.warehouse_health.verify_manifest",
               return_value={"rows": 9, "sha256": "abc"}):
        result = check_warehouse(report)
    assert any("event count" in issue for issue in result["issues"])
