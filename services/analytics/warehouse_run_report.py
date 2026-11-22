"""Structured status report for an explicitly invoked warehouse batch.

A failed batch writes diagnostics without masking the original exception.
"""
import argparse
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from services.analytics.warehouse_batch import run_warehouse_batch


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".run-report-", suffix=".json", delete=False,
        ) as handle:
            temporary = handle.name
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def run_reported_batch(db_path, workspace, report_path, *, dbt_executable="dbt"):
    """Run one batch and persist a success/failure report at a caller-owned path."""
    workspace = Path(workspace).resolve()
    report_path = Path(report_path).resolve()
    source = Path(db_path).resolve()
    if report_path == source:
        raise ValueError("Report cannot overwrite the SQLite database")
    if report_path == workspace or workspace in report_path.parents:
        raise ValueError("Report must be outside the batch workspace")
    run_id = uuid4().hex
    started = _utc_now()
    tick = time.monotonic()
    report = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at_utc": started,
        "status": "running",
    }
    error = None
    try:
        result = run_warehouse_batch(source, workspace, dbt_executable=dbt_executable)
        report["status"] = "success"
        report["result"] = result
    except Exception as exc:
        report["status"] = "failure"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)[:1000]}
        error = exc
    finally:
        report["finished_at_utc"] = _utc_now()
        report["duration_seconds"] = round(time.monotonic() - tick, 3)
        _atomic_json(report_path, report)
    if error is not None:
        raise error
    return report


def main():
    parser = argparse.ArgumentParser(description="Build warehouse and write a JSON run report")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    print(json.dumps(run_reported_batch(args.db_path, args.workspace, args.report), indent=2))


if __name__ == "__main__":
    main()
