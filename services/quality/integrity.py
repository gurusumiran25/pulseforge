"""Read-only database integrity and session consistency checks."""

import sqlite3
from datetime import datetime
from pathlib import Path


def _connect_readonly(path):
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def audit_integrity(event_db, customer_db):
    issues = []
    metrics = {}

    with _connect_readonly(event_db) as events:
        integrity = events.execute("PRAGMA quick_check").fetchone()[0]
        metrics["sqlite_integrity"] = integrity

        if integrity != "ok":
            issues.append({
                "event_id": None,
                "issue": "SQLITE_INTEGRITY_FAILURE",
            })

        duplicates = events.execute("""
            SELECT user_id, session_id, event_name, event_time,
                   COUNT(*) AS n
            FROM events
            GROUP BY user_id, session_id, event_name, event_time
            HAVING COUNT(*) > 1
        """).fetchall()

        metrics["potential_duplicate_activity_groups"] = len(duplicates)

        for user_id, session_id, event_name, event_time, count in duplicates:
            issues.append({
                "event_id": None,
                "issue": "POTENTIAL_DUPLICATE_ACTIVITY",
                "user_id": user_id,
                "session_id": session_id,
                "event_name": event_name,
                "event_time": event_time,
                "count": count,
            })

        mixed_sessions = events.execute("""
            SELECT session_id, COUNT(DISTINCT user_id)
            FROM events
            GROUP BY session_id
            HAVING COUNT(DISTINCT user_id) > 1
        """).fetchall()

        metrics["mixed_customer_sessions"] = len(mixed_sessions)

        for session_id, customer_count in mixed_sessions:
            issues.append({
                "event_id": None,
                "issue": "MULTI_CUSTOMER_SESSION",
                "session_id": session_id,
                "customer_count": customer_count,
            })

        metrics["empty_session_events"] = events.execute("""
            SELECT COUNT(*)
            FROM events
            WHERE session_id IS NULL OR TRIM(session_id) = ''
        """).fetchone()[0]

        if metrics["empty_session_events"]:
            issues.append({
                "event_id": None,
                "issue": "EMPTY_SESSION_ID",
                "count": metrics["empty_session_events"],
            })

    with _connect_readonly(customer_db) as registry:
        invalid_dates = 0

        for customer_id, first_seen, last_seen in registry.execute("""
            SELECT customer_id, first_seen, last_seen
            FROM customers
        """):
            try:
                first = datetime.fromisoformat(first_seen)
                last = datetime.fromisoformat(last_seen)

                if (
                    first.tzinfo is None
                    or last.tzinfo is None
                    or first.utcoffset() is None
                    or last.utcoffset() is None
                    or first > last
                ):
                    raise ValueError("Invalid customer date range")

            except (ValueError, TypeError):
                invalid_dates += 1
                issues.append({
                    "event_id": None,
                    "issue": "INVALID_CUSTOMER_DATE_RANGE",
                    "customer_id": customer_id,
                })

        metrics["invalid_customer_date_ranges"] = invalid_dates

    return {
        "status": "PASS" if not issues else "REVIEW",
        "metrics": metrics,
        "issues": issues,
    }
