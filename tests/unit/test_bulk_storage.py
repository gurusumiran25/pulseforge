from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


def test_bulk_insert_stores_all_events(tmp_path):
    store = SQLiteEventStore(tmp_path / "bulk.db")
    events = generate_customer_journey(seed=42)

    result = store.insert_events_bulk(events)

    assert result["inserted"] == len(events)
    assert result["duplicates"] == 0
    assert store.count_events() == len(events)


def test_bulk_insert_detects_duplicates(tmp_path):
    store = SQLiteEventStore(tmp_path / "bulk.db")
    events = generate_customer_journey(seed=42)

    store.insert_events_bulk(events)
    result = store.insert_events_bulk(events)

    assert result["inserted"] == 0
    assert result["duplicates"] == len(events)
    assert store.count_events() == len(events)


def test_bulk_insert_handles_empty_list(tmp_path):
    store = SQLiteEventStore(tmp_path / "bulk.db")

    result = store.insert_events_bulk([])

    assert result == {"inserted": 0, "duplicates": 0}
    assert store.count_events() == 0


def test_bulk_insert_handles_duplicates_within_batch(tmp_path):
    store = SQLiteEventStore(tmp_path / "bulk.db")
    event = generate_customer_journey(seed=42)[0]

    result = store.insert_events_bulk([event, event])

    assert result == {"inserted": 1, "duplicates": 1}
    assert store.count_events() == 1
