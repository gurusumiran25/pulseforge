"""Idempotent monitoring snapshot storage for PulseForge M18."""

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def make_run_key(snapshot, run_id):
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id must be a non-empty string")

    identity = {
        "schema_version": snapshot["schema_version"],
        "run_id": run_id,
    }

    payload = json.dumps(identity, sort_keys=True)

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def save_once(snapshot, run_id, db_path):
    """Persist at most one snapshot per run key.

    Returns (snapshot_id, created).
    """
    run_key = make_run_key(snapshot, run_id)
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(
        snapshot,
        sort_keys=True,
        allow_nan=False,
    )

    with closing(sqlite3.connect(path, timeout=30)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_idempotent_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_key TEXT NOT NULL UNIQUE,
                    run_id TEXT NOT NULL,
                    generated_at_utc TEXT NOT NULL,
                    overall_status TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
            """)

            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO monitoring_idempotent_snapshots (
                    run_key,
                    run_id,
                    generated_at_utc,
                    overall_status,
                    snapshot_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_key,
                    run_id,
                    snapshot["generated_at_utc"],
                    snapshot["overall_status"],
                    payload,
                ),
            )

            created = cursor.rowcount == 1

            row = connection.execute(
                """
                SELECT id FROM monitoring_idempotent_snapshots
                WHERE run_key = ?
                """,
                (run_key,),
            ).fetchone()

            if row is None:
                raise RuntimeError(
                    "Snapshot could not be verified"
                )

            return row[0], created
