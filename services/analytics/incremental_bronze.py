"""Idempotent Bronze snapshot refresh using event_id as the durable checkpoint.

The existing CSV is the checkpoint: no separate state file can drift from output.
This performs a full SQLite scan, not a database-level incremental query.
"""
import csv
import os
import tempfile
from pathlib import Path

from services.analytics.bronze_export import FIELDS
from services.storage.sqlite_store import SQLiteEventStore


def refresh_bronze(db_path, output_path):
    source = Path(db_path)
    output = Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(f"SQLite event database does not exist: {source}")
    if source.resolve() == output.resolve():
        raise ValueError("Output must not overwrite source database")

    previous = {}
    if output.exists():
        with output.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != FIELDS:
                raise ValueError("Existing Bronze CSV has incompatible schema")
            for row in reader:
                if not all(row.get(field) for field in FIELDS):
                    raise ValueError("Existing Bronze CSV contains blank required fields")
                key = row["event_id"]
                if key in previous:
                    raise ValueError("Existing Bronze CSV contains duplicate event_id")
                previous[key] = row

    with SQLiteEventStore(source).connect() as connection:
        connection.execute("BEGIN")
        current = {
            row["event_id"]: {field: row[field] for field in FIELDS}
            for row in connection.execute(
                "SELECT event_id, event_name, session_id, user_id, event_time "
                "FROM events ORDER BY event_id"
            )
        }
    if not previous.keys() <= current.keys():
        raise ValueError("Existing Bronze contains events missing from SQLite source")
    if any(current[key] != row for key, row in previous.items()):
        raise ValueError("Existing Bronze contains modified event records")

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8", dir=output.parent,
            prefix=".bronze-refresh-", suffix=".csv", delete=False,
        ) as handle:
            temp_name = handle.name
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for key in sorted(current):
                writer.writerow(current[key])
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, output)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return {"total": len(current), "added": len(current) - len(previous)}
