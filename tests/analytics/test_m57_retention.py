"""M57 exact-day cohort retention regression tests."""
from datetime import datetime, timezone

import pytest

from services.analytics.retention import calculate_retention


def event(user, timestamp):
    return {"user_id": user, "event_time": timestamp}


def test_exact_day_retention_and_no_double_counting():
    events = [
        event("a", "2026-11-01T23:30:00+00:00"),
        event("a", "2026-11-02T01:00:00+00:00"),
        event("a", "2026-11-02T03:00:00+00:00"),
        event("b", "2026-11-01T09:00:00Z"),
        event("b", "2026-11-08T09:00:00Z"),
    ]
    row = calculate_retention(events)["cohorts"][0]
    assert row["users"] == 2
    assert row["day_1_users"] == 1
    assert row["day_1_retention_pct"] == 50.0
    assert row["day_7_users"] == 1
    assert row["day_7_retention_pct"] == 50.0


def test_utc_normalization_across_offsets():
    events = [
        event("a", "2026-11-02T00:30:00+05:30"),
        event("a", "2026-11-02T23:30:00+05:30"),
    ]
    rows = calculate_retention(events)["cohorts"]
    assert rows[0]["cohort_date_utc"] == "2026-11-01"
    assert rows[0]["day_1_users"] == 1


def test_datetime_and_empty_data():
    assert calculate_retention([])["cohorts"] == []
    result = calculate_retention([event("a", datetime(2026, 11, 1, tzinfo=timezone.utc))])
    assert result["cohorts"][0]["day_1_users"] == 0


@pytest.mark.parametrize("value", ["2026-11-01T00:00:00", "invalid"])
def test_invalid_timestamps(value):
    with pytest.raises(ValueError):
        calculate_retention([event("a", value)])


@pytest.mark.parametrize("horizons", [(), (0,), (-1,), (1, 1), (True,)])
def test_invalid_horizons(horizons):
    with pytest.raises(ValueError):
        calculate_retention([], horizons=horizons)
