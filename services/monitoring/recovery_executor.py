"""Bounded recovery execution with JSONL audit logging.

M18 Stage 9: isolated execution primitives only.
"""

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from services.monitoring.failure_classifier import classify_failure


def append_audit(log_path, record):
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **record,
    }

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, sort_keys=True) + "\n")


def execute_bounded_retry(
    operation,
    *,
    run_id,
    audit_path,
    max_attempts=3,
    delay_seconds=0,
):
    """Retry only transient SQLite busy/locked failures."""

    if not callable(operation):
        raise TypeError("operation must be callable")

    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id must be non-empty")

    if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
        raise ValueError("max_attempts must be between 1 and 3")

    if not isinstance(delay_seconds, (int, float)):
        raise TypeError("delay_seconds must be numeric")

    if not 0 <= delay_seconds <= 5:
        raise ValueError("delay_seconds must be between 0 and 5")

    for attempt in range(1, max_attempts + 1):
        try:
            result = operation()

        except Exception as error:
            classification = classify_failure(error=error)

            retryable = (
                classification["category"] == "TRANSIENT"
                and classification["code"] == "SQLITE_BUSY"
            )

            append_audit(audit_path, {
                "run_id": run_id,
                "attempt": attempt,
                "outcome": "RETRY" if (
                    retryable and attempt < max_attempts
                ) else "FAILED",
                "failure_code": classification["code"],
            })

            if not retryable or attempt == max_attempts:
                raise

            time.sleep(delay_seconds)

        else:
            append_audit(audit_path, {
                "run_id": run_id,
                "attempt": attempt,
                "outcome": "SUCCESS",
                "failure_code": None,
            })

            return result

    raise RuntimeError("Unreachable retry state")
