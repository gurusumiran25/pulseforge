from datetime import datetime, timezone

import pytest

from apps.dashboard.metrics import filter_complete_sessions, load_events, summarize


def test_cohort_filter_keeps_cross_midnight_payment():
    events = filter_complete_sessions(load_events(), "2026-11-19", "2026-11-19")
    result = summarize(events)
    assert result["events"] == 4
    assert result["sessions"] == 1
    assert result["paid_sessions"] == 1
    assert result["daily_funnel"][0]["date"] == "2026-11-19"
    assert result["daily_activity"][-1]["date"] == "2026-11-20"


def test_next_day_cohort_excludes_previous_day_session():
    events = filter_complete_sessions(load_events(), "2026-11-20", "2026-11-20")
    result = summarize(events)
    assert result["events"] == 2
    assert result["sessions"] == 2
    assert result["paid_sessions"] == 0


def test_reversed_date_range_rejected():
    with pytest.raises(ValueError, match="start_date"):
        filter_complete_sessions(load_events(), "2026-11-20", "2026-11-19")
