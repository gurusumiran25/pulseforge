"""Atomic, one-snapshot-per-run M17-compatible storage."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from services.monitoring.idempotent_store import make_run_key


def save_run_once(snapshot, run_id, db_path):
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id must be non-empty")

    if not isinstance(snapshot, dict):
        raise ValueError("snapshot must be a dictionary")

    generated = snapshot["generated_at_utc"]
    status = snapshot["overall_status"]
    alerts = snapshot["alerts"]

    if not isinstance(generated, str) or not generated:
        raise ValueError("Invalid generation timestamp")
    if not isinstance(status, str) or not status:
        raise ValueError("Invalid monitoring status")
    if not isinstance(alerts, list):
        raise ValueError("alerts must be a list")

    run_key = make_run_key(snapshot, run_id)
    payload = json.dumps(snapshot, sort_keys=True, allow_nan=False)

    path = Path(db_path)

    if not path.parent.is_dir():
        raise FileNotFoundError(
            "Monitoring database parent directory does not exist"
        )

    with closing(sqlite3.connect(path, timeout=30)) as connection:
        connection.execute("PRAGMA busy_timeout = 30000")

        with connection:
            connection.execute("BEGIN IMMEDIATE")

            connection.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generated_at_utc TEXT NOT NULL,
                    overall_status TEXT NOT NULL,
                    alert_count INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
            """)

            connection.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_run_registry (
                    run_key TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    snapshot_id INTEGER NOT NULL UNIQUE,
                    FOREIGN KEY(snapshot_id)
                        REFERENCES monitoring_snapshots(id)
                )
            """)

            # Fail closed if legacy data already violates uniqueness.
            connection.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                    ux_monitoring_run_registry_run_id
                ON monitoring_run_registry(run_id)
            """)

            existing = connection.execute("""
                SELECT snapshot_id
                FROM monitoring_run_registry
                WHERE run_id = ?
            """, (run_id,)).fetchone()

            if existing is not None:
                return existing[0], False

            cursor = connection.execute("""
                INSERT INTO monitoring_snapshots (
                    generated_at_utc,
                    overall_status,
                    alert_count,
                    snapshot_json
                ) VALUES (?, ?, ?, ?)
            """, (
                generated,
                status,
                len(alerts),
                payload,
            ))

            snapshot_id = cursor.lastrowid

            connection.execute("""
                INSERT INTO monitoring_run_registry (
                    run_key, run_id, snapshot_id
                ) VALUES (?, ?, ?)
            """, (run_key, run_id, snapshot_id))

            return snapshot_id, True
