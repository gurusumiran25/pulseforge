"""Read-only event quality scanner for PulseForge."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from contracts.event_validation import EventEnvelope


def _connect_readonly(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Database not found: {path}")

    uri = path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def scan_events(
    event_db="data/automation/events.db",
    customer_db="data/automation/customers.db",
):
    issues = []
    checked = 0

    with _connect_readonly(customer_db) as customers_conn:
        customers = {
            row[0]
            for row in customers_conn.execute(
                "SELECT customer_id FROM customers"
            )
        }

    with _connect_readonly(event_db) as events_conn:
        cursor = events_conn.execute(
            """
            SELECT event_id, event_name, user_id,
                   session_id, event_time, ingested_at, payload
            FROM events
            """
        )

        for row in cursor:
            checked += 1
            (
                event_id, event_name, user_id,
                session_id, event_time, ingested_at, payload
            ) = row

            def flag(code):
                issues.append({
                    "event_id": event_id,
                    "issue": code,
                })

            try:
                event = EventEnvelope.model_validate_json(payload)
            except (ValidationError, ValueError, TypeError):
                flag("INVALID_EVENT_PAYLOAD")
                continue

            for field, stored, parsed in (
                ("event_id", event_id, event.event_id),
                ("event_name", event_name, event.event_name),
                ("user_id", user_id, event.user_id),
                ("session_id", session_id, event.session_id),
            ):
                if stored != parsed:
                    flag(f"{field.upper()}_MISMATCH")

            if user_id not in customers:
                flag("UNKNOWN_CUSTOMER")

            for field, stored, parsed in (
                ("event_time", event_time, event.event_time),
                ("ingested_at", ingested_at, event.ingested_at),
            ):
                try:
                    timestamp = datetime.fromisoformat(stored)
                    if (
                        timestamp.tzinfo is None
                        or timestamp.utcoffset() is None
                    ):
                        raise ValueError("Timezone missing")

                    if parsed is None or (
                        timestamp.astimezone(timezone.utc)
                        != parsed.astimezone(timezone.utc)
                    ):
                        flag(f"{field.upper()}_MISMATCH")
                except (ValueError, TypeError, AttributeError):
                    flag(f"INVALID_{field.upper()}")

    return {
        "total_events": checked,
        "total_issues": len(issues),
        "events_with_issues": len({
            issue["event_id"] for issue in issues
        }),
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
    }


if __name__ == "__main__":
    print(json.dumps(scan_events(), indent=2))
