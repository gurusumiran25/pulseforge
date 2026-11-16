import json
from datetime import datetime, timezone
from pathlib import Path


def write_run_log(log_path, status, run_date, details=None):
    if status not in {"started", "completed", "failed", "skipped"}:
        raise ValueError("Invalid run status")

    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "run_date": run_date,
        "status": status,
        "details": details or {},
    }

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, default=str) + "\n")

    return record
