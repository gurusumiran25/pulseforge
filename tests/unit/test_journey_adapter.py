from datetime import datetime, timedelta, timezone

import pytest

from contracts.event_validation import EventEnvelope
from services.simulation.journey_adapter import generate_planned_journey
from services.simulation.session_planner import (
    PlannedSession,
    plan_daily_sessions,
)


def make_session(customer_id="customer-001", session_id="session-001"):
    return PlannedSession(
        customer_id=customer_id,
        session_id=session_id,
        session_start=datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc),
        segment="casual_browser",
    )


def test_generated_events_follow_planned_identity():
    session = make_session()
    events = generate_planned_journey(session)

    assert events
    assert all(e.user_id == session.customer_id for e in events)
    assert all(e.session_id == session.session_id for e in events)


def test_generated_events_pass_contract_validation():
    events = generate_planned_journey(make_session())

    for event in events:
        EventEnvelope.model_validate(event.model_dump())


def test_journey_is_repeatable():
    session = make_session()

    first = generate_planned_journey(session)
    second = generate_planned_journey(session)

    assert [e.model_dump() for e in first] == [
        e.model_dump() for e in second
    ]


def test_event_ids_are_unique_across_sessions():
    sessions = plan_daily_sessions(
        [f"customer-{i}" for i in range(50)],
        datetime(2026, 11, 2, tzinfo=timezone.utc),
    )

    events = [
        event
        for session in sessions
        for event in generate_planned_journey(session)
    ]

    assert len({e.event_id for e in events}) == len(events)


def test_event_times_follow_session_start():
    session = make_session()
    events = generate_planned_journey(session)

    assert events[0].event_time == session.session_start

    for index, event in enumerate(events):
        assert event.event_time == (
            session.session_start + timedelta(seconds=index * 30)
        )


def test_order_ids_unique_across_sessions():
    sessions = plan_daily_sessions(
        [f"customer-{i}" for i in range(50)],
        datetime(2026, 11, 2, tzinfo=timezone.utc),
    )

    orders = [
        event.properties["order_id"]
        for session in sessions
        for event in generate_planned_journey(session)
        if event.event_name in ("payment_succeeded", "payment_failed")
    ]

    assert len(orders) == len(set(orders))


def test_invalid_session_type_rejected():
    with pytest.raises(ValueError, match="PlannedSession"):
        generate_planned_journey("not-a-session")


def test_empty_customer_id_rejected():
    session = make_session(customer_id="")

    with pytest.raises(ValueError, match="customer_id"):
        generate_planned_journey(session)


def test_empty_session_id_rejected():
    session = make_session(session_id="")

    with pytest.raises(ValueError, match="session_id"):
        generate_planned_journey(session)


def test_naive_session_timestamp_rejected():
    session = PlannedSession(
        customer_id="customer-001",
        session_id="session-001",
        session_start=datetime(2026, 11, 2, 12, 0),
        segment="casual_browser",
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        generate_planned_journey(session)
