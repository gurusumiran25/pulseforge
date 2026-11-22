"""Immutable incremental Bronze chunks, published by atomic directory rename."""
import csv
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from services.analytics.bronze_export import FIELDS
from services.analytics.bronze_manifest import verify_manifest, write_manifest


def publish_chunk(db_path, snapshots_root, *, after_rowid=0, chunk_name=None):
    if type(after_rowid) is not int or after_rowid < 0:
        raise ValueError("after_rowid must be a nonnegative integer")
    source = Path(db_path).resolve()
    root = Path(snapshots_root).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"SQLite database not found: {source}")
    if source == root or root in source.parents:
        raise ValueError("Snapshot root cannot contain source database")
    name = chunk_name or f"after-{after_rowid:020d}"
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError("chunk_name must be a single directory name")
    root.mkdir(parents=True, exist_ok=True)
    destination = root / name
    if destination.exists():
        raise FileExistsError(f"Snapshot already exists: {destination}")
    with tempfile.TemporaryDirectory(prefix=".bronze-publish-", dir=root) as temporary:
        staging = Path(temporary)
        csv_path = staging / "bronze_events.csv"
        highest = after_rowid
        rows = 0
        with sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN")
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(FIELDS)
                for record in connection.execute(
                    "SELECT rowid, event_id, event_name, session_id, user_id, event_time "
                    "FROM events WHERE rowid > ? ORDER BY rowid", (after_rowid,),
                ):
                    writer.writerow([record[field] for field in FIELDS])
                    highest = record["rowid"]
                    rows += 1
                handle.flush()
                os.fsync(handle.fileno())
        manifest_path = staging / "bronze.manifest.json"
        manifest = write_manifest(csv_path, manifest_path)
        verify_manifest(csv_path, manifest_path)
        checkpoint = {"after_rowid": after_rowid, "next_rowid": highest,
                      "rows": rows, "sha256": manifest["sha256"]}
        with (staging / "checkpoint.json").open("w", encoding="utf-8") as handle:
            json.dump(checkpoint, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if destination.exists():
            raise FileExistsError(f"Snapshot already exists: {destination}")
        os.rename(staging, destination)
    return {**checkpoint, "snapshot": str(destination)}
