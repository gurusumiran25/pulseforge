from datetime import datetime, timezone

from services.simulation.journey_adapter import generate_planned_journey
from services.simulation.session_planner import plan_daily_sessions
from services.storage.sqlite_store import SQLiteEventStore


def generate_test_events():
    customers = [f"test-customer-{i:03d}" for i in range(20)]
    sessions = plan_daily_sessions(
        customers,
        datetime(2026, 11, 2, tzinfo=timezone.utc),
        seed=42,
    )
    events = [
        event
        for session in sessions
        for event in generate_planned_journey(session)
    ]
    return customers, sessions, events


def test_planned_journeys_persist_to_sqlite(tmp_path):
    customers, sessions, events = generate_test_events()

    store = SQLiteEventStore(tmp_path / "events.db")
    store.connect()

    for event in events:
        store.insert_event(event)

    assert store.count_events() == len(events)
    assert len({event.event_id for event in events}) == len(events)
    assert len({event.session_id for event in events}) == len(sessions)
    assert len({event.user_id for event in events}) == len(customers)

    for event in events:
        stored = store.get_event(event.event_id)
        assert stored is not None


def test_replaying_journeys_does_not_duplicate_events(tmp_path):
    _, _, events = generate_test_events()

    store = SQLiteEventStore(tmp_path / "events.db")
    store.connect()

    for event in events:
        store.insert_event(event)

    first_count = store.count_events()

    for event in events:
        store.insert_event(event)

    assert first_count == len(events)
    assert store.count_events() == first_count
