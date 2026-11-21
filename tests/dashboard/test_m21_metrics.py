"""M21 dashboard contract tests; no Streamlit runtime required."""
import csv
from pathlib import Path

import pytest

from apps.dashboard.metrics import load_events, summarize


def test_synthetic_seed_metrics():
    result = summarize(load_events())
    assert (result["events"], result["sessions"], result["users"], result["paid_sessions"]) == (6, 3, 3, 1)
    assert result["daily_funnel"] == [
        {"date": "2026-11-19", "sessions": 1, "product_viewed": 1,
         "add_to_cart": 1, "checkout_started": 1, "payment_succeeded": 1},
        {"date": "2026-11-20", "sessions": 2, "product_viewed": 1,
         "add_to_cart": 0, "checkout_started": 0, "payment_succeeded": 0},
    ]
    assert result["daily_activity"] == [
        {"date": "2026-11-19", "events": 2, "active_users": 1},
        {"date": "2026-11-20", "events": 4, "active_users": 3},
    ]


def test_empty_filtered_events():
    result = summarize([])
    assert result["events"] == result["sessions"] == result["paid_sessions"] == 0
    assert result["daily_funnel"] == result["daily_activity"] == []


def test_reject_duplicate_event_ids(tmp_path):
    path = tmp_path / "duplicate.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["event_id", "event_name", "session_id", "user_id", "event_time"])
        writer.writerow(["same", "page_view", "s1", "u1", "2026-11-19 00:00:00"])
        writer.writerow(["same", "page_view", "s2", "u2", "2026-11-19 01:00:00"])
    with pytest.raises(ValueError, match="Duplicate event_id"):
        load_events(path)


def test_session_stage_flags_not_chronological():
    event = {
        "event_id": "pay", "event_name": "payment_succeeded", "session_id": "direct",
        "user_id": "u1", "event_time": load_events()[0]["event_time"]
    }
    result = summarize([event])
    row = result["session_rows"][0]
    assert row["payment_succeeded"] == 1
    assert row["product_viewed"] == row["add_to_cart"] == row["checkout_started"] == 0
