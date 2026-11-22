"""M39 run diagnostics and fail-closed reporting."""
import json
from unittest.mock import patch

import pytest

from services.analytics.warehouse_run_report import run_reported_batch
from services.storage.sqlite_store import SQLiteEventStore


def test_success_report_contains_run_metadata(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    report_path = tmp_path / "run.json"
    with patch("services.analytics.warehouse_run_report.run_warehouse_batch",
               return_value={"events_exported": 2, "warehouse": "isolated.duckdb"}):
        result = run_reported_batch(store.db_path, tmp_path / "workspace", report_path)
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved == result
    assert saved["status"] == "success"
    assert saved["result"]["events_exported"] == 2
    assert saved["duration_seconds"] >= 0
    assert saved["run_id"]


def test_failure_report_preserves_original_exception(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    report_path = tmp_path / "failed.json"
    with patch("services.analytics.warehouse_run_report.run_warehouse_batch",
               side_effect=RuntimeError("dbt exited with code 1")):
        with pytest.raises(RuntimeError, match="dbt exited"):
            run_reported_batch(store.db_path, tmp_path / "workspace", report_path)
    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert saved["status"] == "failure"
    assert saved["error"]["type"] == "RuntimeError"
    assert "dbt exited" in saved["error"]["message"]
    assert "result" not in saved


def test_report_cannot_overwrite_source_or_workspace(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    with pytest.raises(ValueError, match="SQLite"):
        run_reported_batch(store.db_path, tmp_path / "workspace", store.db_path)
    with pytest.raises(ValueError, match="outside"):
        run_reported_batch(store.db_path, tmp_path / "workspace", tmp_path / "workspace/run.json")
