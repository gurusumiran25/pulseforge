"""Validated, deterministic monitoring run identity."""

import json
from datetime import date
from pathlib import Path


def resolve_completed_run(log_path, run_date):
    """Resolve a completed daily simulation without executing it."""

    if not isinstance(run_date, str):
        raise TypeError("run_date must be a string")

    try:
        parsed = date.fromisoformat(run_date)
    except ValueError as error:
        raise ValueError("Invalid ISO run date") from error

    if parsed.isoformat() != run_date:
        raise ValueError("Run date must use YYYY-MM-DD")

    path = Path(log_path)

    if not path.is_file():
        raise FileNotFoundError(f"Simulation ledger missing: {path}")

    matches = []

    for number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid ledger JSON at line {number}"
            ) from error

        if not isinstance(record, dict):
            raise ValueError(
                f"Invalid ledger record at line {number}"
            )

        if record.get("run_date") == run_date:
            matches.append(record)

    if not matches:
        raise RuntimeError(
            f"No ledger record for {run_date}"
        )

    if matches[-1].get("status") != "completed":
        raise RuntimeError(
            f"Latest ledger status for {run_date} is not completed"
        )

    completed = [
        record for record in matches
        if record.get("status") == "completed"
    ]

    details = completed[-1].get("details")

    if not isinstance(details, dict):
        raise RuntimeError("Completed run details missing")

    if details.get("run_date") != run_date:
        raise RuntimeError("Completed run date mismatch")

    events_after = details.get("events_after")

    if type(events_after) is not int or events_after < 0:
        raise RuntimeError("Invalid completed event count")

    return {
        "run_id": f"pulseforge-daily:{run_date}",
        "run_date": run_date,
        "status": "completed",
        "events_after": events_after,
        "completed_entries": len(completed),
    }
