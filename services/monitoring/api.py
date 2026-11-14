"""Read-only FastAPI endpoints for PulseForge monitoring."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from services.monitoring.snapshot_store import (
    DEFAULT_DB,
    get_latest_snapshot,
)


app = FastAPI(
    title="PulseForge Monitoring API",
    version="0.1.0",
)


def _monitoring_connection():
    path = Path(DEFAULT_DB)

    if not path.is_file():
        raise FileNotFoundError("Monitoring database unavailable")

    return sqlite3.connect(
        path.resolve().as_uri() + "?mode=ro",
        uri=True,
    )


@app.get("/monitoring/health")
def monitoring_health():
    try:
        with closing(_monitoring_connection()) as connection:
            result = connection.execute(
                "PRAGMA quick_check"
            ).fetchone()

            if result is None or result[0] != "ok":
                raise sqlite3.DatabaseError(
                    "Monitoring database integrity check failed"
                )
    except (OSError, sqlite3.Error) as exc:
        raise HTTPException(
            status_code=503,
            detail="Monitoring database unavailable",
        ) from exc

    return {
        "status": "available",
        "service": "pulseforge-monitoring",
        "note": "API/database availability only; not platform health",
    }


@app.get("/monitoring/latest")
def monitoring_latest():
    try:
        snapshot = get_latest_snapshot(db_path=DEFAULT_DB)
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Unable to read latest monitoring snapshot",
        ) from exc

    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="No monitoring snapshots available",
        )

    return snapshot


@app.get("/monitoring/history")
def monitoring_history(limit: int = Query(default=10, ge=1, le=100)):
    try:
        with closing(_monitoring_connection()) as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    generated_at_utc,
                    overall_status,
                    alert_count
                FROM monitoring_snapshots
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    except (OSError, sqlite3.Error) as exc:
        raise HTTPException(
            status_code=503,
            detail="Unable to read monitoring history",
        ) from exc

    return {
        "count": len(rows),
        "snapshots": [
            {
                "snapshot_id": row[0],
                "generated_at_utc": row[1],
                "overall_status": row[2],
                "alert_count": row[3],
            }
            for row in rows
        ],
    }


if __name__ == "__main__":
    print(json.dumps({
        "health": monitoring_health(),
        "latest": {
            "snapshot_id": monitoring_latest()["snapshot_id"],
            "overall_status": monitoring_latest()["overall_status"],
        },
        "history": monitoring_history(limit=10),
    }, indent=2))
