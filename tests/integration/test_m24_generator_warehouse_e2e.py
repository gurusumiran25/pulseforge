"""M24: generator -> validated envelopes -> SQLite -> warehouse SQL -> KPIs.

Uses a disposable pytest database. This does NOT exercise Kafka, FastAPI, dbt
or the Streamlit UI; those require separate integration coverage.
"""
from pathlib import Path

import pytest

from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


VIEWS = Path(__file__).resolve().parents[2] / "warehouse/sql/m20_views.sql"


@pytest.fixture
def pipeline(tmp_path):
    store = SQLiteEventStore(tmp_path / "m24-events.db")
    journeys = [generate_customer_journey(seed=i) for i in range(40)]
    events = [event for journey in journeys for event in journey]
    assert all(event.schema_version == 1 for event in events)
    result = store.insert_events_bulk(events)
    assert result == {"inserted": len(events), "duplicates": 0}
    with store.connect() as conn:
        conn.executescript(VIEWS.read_text(encoding="utf-8"))
    return store, journeys, events


def test_generated_events_survive_storage_and_silver(pipeline):
    store, journeys, events = pipeline
    assert store.count_events() == len(events)
    with store.connect() as conn:
        rows = conn.execute("select event_id, event_name, session_id from silver_events").fetchall()
    assert len(rows) == len(events)
    assert {row["event_id"] for row in rows} == {event.event_id for event in events}
    for event in events:
        persisted = store.get_event(event.event_id)
        assert persisted is not None
        assert persisted.event_name == event.event_name
        assert persisted.session_id == event.session_id


def test_session_gold_matches_independent_generated_journeys(pipeline):
    store, journeys, events = pipeline
    expected = {}
    for journey in journeys:
        session = journey[0].session_id
        names = {event.event_name for event in journey}
        expected[session] = (
            len(journey),
            int("product_viewed" in names),
            int("add_to_cart" in names),
            int("checkout_started" in names),
            int("payment_succeeded" in names),
        )
    with store.connect() as conn:
        rows = conn.execute(
            "select session_id, event_count, viewed_product, added_to_cart, "
            "started_checkout, completed_payment from gold_session_funnel"
        ).fetchall()
    assert len(rows) == len(journeys)
    for row in rows:
        assert tuple(row[field] for field in (
            "event_count", "viewed_product", "added_to_cart",
            "started_checkout", "completed_payment"
        )) == expected[row["session_id"]]


def test_daily_gold_matches_session_cohorts(pipeline):
    store, journeys, events = pipeline
    expected = {}
    for journey in journeys:
        day = min(event.event_time for event in journey).date().isoformat()
        bucket = expected.setdefault(day, [0, 0, 0, 0, 0])
        names = {event.event_name for event in journey}
        bucket[0] += 1
        for index, name in enumerate(
            ("product_viewed", "add_to_cart", "checkout_started", "payment_succeeded"),
            start=1,
        ):
            bucket[index] += int(name in names)
    with store.connect() as conn:
        rows = conn.execute(
            "select cohort_date_utc, sessions, sessions_with_product_view, "
            "sessions_with_cart, sessions_with_checkout, sessions_with_payment "
            "from gold_daily_funnel"
        ).fetchall()
    assert {row[0]: list(row)[1:] for row in rows} == expected


def test_bulk_replay_is_idempotent(pipeline):
    store, journeys, events = pipeline
    replay = store.insert_events_bulk(events)
    assert replay == {"inserted": 0, "duplicates": len(events)}
    assert store.count_events() == len(events)
    with store.connect() as conn:
        assert conn.execute("select sum(event_count) from gold_session_funnel").fetchone()[0] == len(events)
