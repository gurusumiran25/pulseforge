"""Backward-compatible, idempotent M18 monitoring snapshot storage."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from services.monitoring.idempotent_store import make_run_key


def save_compatible_once(snapshot, run_id, db_path):
    """Atomically insert into M17 storage at most once per run key.

    Returns (snapshot_id, created).
    """

    run_key = make_run_key(snapshot, run_id)
    payload = json.dumps(snapshot, sort_keys=True, allow_nan=False)

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(path, timeout=30)) as conn:
        conn.execute("PRAGMA busy_timeout = 30000")

        with conn:
            conn.execute("BEGIN IMMEDIATE")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    generated_at_utc TEXT NOT NULL,
                    overall_status TEXT NOT NULL,
                    alert_count INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_run_registry (
                    run_key TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    snapshot_id INTEGER NOT NULL UNIQUE,
                    FOREIGN KEY(snapshot_id)
                        REFERENCES monitoring_snapshots(id)
                )
            """)

            existing = conn.execute("""
                SELECT snapshot_id
                FROM monitoring_run_registry
                WHERE run_key = ?
            """, (run_key,)).fetchone()

            if existing is not None:
                return existing[0], False

            cursor = conn.execute("""
                INSERT INTO monitoring_snapshots (
                    generated_at_utc,
                    overall_status,
                    alert_count,
                    snapshot_json
                ) VALUES (?, ?, ?, ?)
            """, (
                snapshot["generated_at_utc"],
                snapshot["overall_status"],
                len(snapshot["alerts"]),
                payload,
            ))

            snapshot_id = cursor.lastrowid

            conn.execute("""
                INSERT INTO monitoring_run_registry (
                    run_key, run_id, snapshot_id
                ) VALUES (?, ?, ?)
            """, (run_key, run_id, snapshot_id))

            return snapshot_id, True
