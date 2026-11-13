"""Isolated regression tests for the PulseForge quality engine."""

import sqlite3

import pytest

from services.quality.integrity import audit_integrity
from services.quality.scoring import classify_issue, score_quality


def make_databases(tmp_path):
    event_db = tmp_path / "events.db"
    customer_db = tmp_path / "customers.db"

    with sqlite3.connect(event_db) as conn:
        conn.execute("""
            CREATE TABLE events (
                event_id TEXT PRIMARY KEY,
                event_name TEXT NOT NULL,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                event_time TEXT NOT NULL
            )
        """)

    with sqlite3.connect(customer_db) as conn:
        conn.execute("""
            CREATE TABLE customers (
                customer_id TEXT PRIMARY KEY,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
        """)

    return event_db, customer_db


def add_event(db, event_id, user_id, session_id, event_time):
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            (event_id, "page_view", user_id, session_id, event_time),
        )


def test_clean_integrity(tmp_path):
    events, customers = make_databases(tmp_path)
    result = audit_integrity(events, customers)

    assert result["status"] == "PASS"
    assert result["issues"] == []


def test_duplicate_activity_detected(tmp_path):
    events, customers = make_databases(tmp_path)
    timestamp = "2026-11-13T10:00:00+00:00"

    add_event(events, "e1", "u1", "s1", timestamp)
    add_event(events, "e2", "u1", "s1", timestamp)

    result = audit_integrity(events, customers)

    assert result["metrics"]["potential_duplicate_activity_groups"] == 1
    assert any(
        issue["issue"] == "POTENTIAL_DUPLICATE_ACTIVITY"
        for issue in result["issues"]
    )


def test_mixed_customer_session_detected(tmp_path):
    events, customers = make_databases(tmp_path)

    add_event(events, "e1", "u1", "shared", "2026-11-13T10:00:00+00:00")
    add_event(events, "e2", "u2", "shared", "2026-11-13T10:01:00+00:00")

    result = audit_integrity(events, customers)

    assert result["metrics"]["mixed_customer_sessions"] == 1


def test_invalid_customer_date_range_detected(tmp_path):
    events, customers = make_databases(tmp_path)

    with sqlite3.connect(customers) as conn:
        conn.execute(
            "INSERT INTO customers VALUES (?, ?, ?)",
            (
                "u1",
                "2026-11-14T10:00:00+00:00",
                "2026-11-13T10:00:00+00:00",
            ),
        )

    result = audit_integrity(events, customers)

    assert result["metrics"]["invalid_customer_date_ranges"] == 1


def test_missing_database_fails_safely(tmp_path):
    with pytest.raises(FileNotFoundError):
        audit_integrity(
            tmp_path / "missing_events.db",
            tmp_path / "missing_customers.db",
        )


def test_clean_quality_score():
    result = score_quality([], 3025)

    assert result["quality_score"] == 100.0
    assert result["grade"] == "EXCELLENT"


def test_high_severity_classification():
    assert classify_issue("INVALID_EVENT_PAYLOAD") == "HIGH"
    assert classify_issue("UNKNOWN_CUSTOMER") == "HIGH"


def test_information_does_not_reduce_score():
    result = score_quality(
        [{"event_id": None, "issue": "INSUFFICIENT_HISTORY"}],
        100,
    )

    assert result["quality_score"] == 100.0
    assert result["severity_counts"]["INFO"] == 1


def test_negative_event_count_rejected():
    with pytest.raises(ValueError):
        score_quality([], -1)
