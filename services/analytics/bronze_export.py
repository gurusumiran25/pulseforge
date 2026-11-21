"""Export committed SQLite events into a dbt-compatible Bronze CSV snapshot.

Explicit invocation only: no background job, broker consumption or database writes.
"""
import argparse
import csv
import os
import tempfile
from pathlib import Path

from services.storage.sqlite_store import SQLiteEventStore


FIELDS = ("event_id", "event_name", "session_id", "user_id", "event_time")


def export_bronze(db_path, output_path):
    """Atomically replace a CSV snapshot using a consistent SQLite read transaction."""
    source = Path(db_path)
    destination = Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(f"SQLite event database does not exist: {source}")
    if source.resolve() == destination.resolve():
        raise ValueError("Output must not overwrite the source database")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", newline="", encoding="utf-8",
            prefix=".pulseforge-bronze-", suffix=".csv",
            dir=destination.parent, delete=False,
        ) as handle:
            temp_name = handle.name
            writer = csv.writer(handle)
            writer.writerow(FIELDS)
            with SQLiteEventStore(source).connect() as connection:
                connection.execute("BEGIN")
                cursor = connection.execute(
                    "SELECT event_id, event_name, session_id, user_id, event_time "
                    "FROM events ORDER BY event_id"
                )
                count = 0
                for row in cursor:
                    writer.writerow([row[field] for field in FIELDS])
                    count += 1
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, destination)
        return count
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def main():
    parser = argparse.ArgumentParser(description="Export SQLite events to dbt Bronze CSV")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(f"Exported {export_bronze(args.db_path, args.output)} events")


if __name__ == "__main__":
    main()
