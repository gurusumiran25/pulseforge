"""Read-only ledger and SQLite consistency checks."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from services.monitoring.run_identity import resolve_completed_run


def verify_run_consistency(log_path, event_db, run_date):
    identity = resolve_completed_run(log_path, run_date)

    records = []

    for number, line in enumerate(
        Path(log_path).read_text(encoding="utf-8").splitlines(),
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
            raise ValueError("Invalid ledger record")

        records.append(record)

    if not records:
        raise RuntimeError("Empty simulation ledger")

    latest = records[-1]

    if (
        latest.get("run_date") != run_date
        or latest.get("status") != "completed"
    ):
        raise RuntimeError(
            "Requested run is not the latest completed ledger entry"
        )

    db = Path(event_db)

    if not db.is_file():
        raise FileNotFoundError(f"Event database missing: {db}")

    uri = db.resolve().as_uri() + "?mode=ro"

    with closing(sqlite3.connect(uri, uri=True)) as connection:
        integrity = connection.execute(
            "PRAGMA quick_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError("Event database integrity failure")

        count = connection.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]

    if count != identity["events_after"]:
        raise RuntimeError(
            "Ledger/database event count mismatch: "
            f"ledger={identity['events_after']}, database={count}"
        )

    return {
        **identity,
        "database_events": count,
        "database_integrity": integrity,
        "consistent": True,
    }
