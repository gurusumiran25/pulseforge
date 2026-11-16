from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest

from services.simulation.session_planner import plan_daily_sessions
from services.simulation.customer_behavior import get_customer_behavior


def utc(day):
    return datetime(2026, 11, day, tzinfo=timezone.utc)


def test_every_customer_has_at_least_one_session():
    customers = [f"customer-{i}" for i in range(100)]

    sessions = plan_daily_sessions(customers, utc(1))
    counts = Counter(s.customer_id for s in sessions)

    assert set(counts) == set(customers)
    assert all(1 <= count <= 3 for count in counts.values())


def test_session_ids_are_unique():
    customers = [f"customer-{i}" for i in range(200)]

    sessions = plan_daily_sessions(customers, utc(1))

    assert len({s.session_id for s in sessions}) == len(sessions)


def test_planning_is_repeatable():
    customers = ["customer-001", "customer-002"]

    first = plan_daily_sessions(customers, utc(1))
    second = plan_daily_sessions(customers, utc(1))

    assert first == second


def test_customer_input_order_does_not_change_results():
    customers = ["customer-001", "customer-002", "customer-003"]

    first = plan_daily_sessions(customers, utc(1))
    second = plan_daily_sessions(list(reversed(customers)), utc(1))

    assert first == second


def test_sessions_are_chronological():
    customers = [f"customer-{i}" for i in range(100)]

    sessions = plan_daily_sessions(customers, utc(1))

    assert sessions == sorted(
        sessions,
        key=lambda s: (s.session_start, s.session_id),
    )


def test_sessions_fall_within_utc_day():
    customers = [f"customer-{i}" for i in range(100)]

    sessions = plan_daily_sessions(customers, utc(1))

    assert all(
        s.session_start.date() == utc(1).date()
        for s in sessions
    )


def test_different_days_have_different_session_ids():
    customers = ["customer-001"]

    first = plan_daily_sessions(customers, utc(1))
    second = plan_daily_sessions(customers, utc(2))

    assert {s.session_id for s in first}.isdisjoint(
        {s.session_id for s in second}
    )


def test_session_segment_matches_customer_profile():
    customers = [f"customer-{i}" for i in range(100)]

    sessions = plan_daily_sessions(customers, utc(1))

    for session in sessions:
        expected = get_customer_behavior(session.customer_id)
        assert session.segment == expected.segment


def test_empty_customer_list_returns_empty_sessions():
    assert plan_daily_sessions([], utc(1)) == []


def test_duplicate_customer_ids_rejected():
    with pytest.raises(ValueError, match="unique"):
        plan_daily_sessions(
            ["customer-001", "customer-001"],
            utc(1),
        )


def test_naive_datetime_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        plan_daily_sessions(
            ["customer-001"],
            datetime(2026, 11, 1),
        )


def test_timezone_normalizes_to_utc():
    india = timezone(timedelta(hours=5, minutes=30))

    sessions = plan_daily_sessions(
        ["customer-001"],
        datetime(2026, 11, 2, 2, 0, tzinfo=india),
    )

    assert all(
        s.session_start.date().isoformat() == "2026-11-01"
        for s in sessions
    )
