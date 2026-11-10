from fastapi.testclient import TestClient

from services.generator.journey_generator import generate_customer_journey
from services.ingestion.main import app, get_event_store
from services.storage.sqlite_store import SQLiteEventStore


def test_sqlite_insert_and_retrieve(tmp_path):
    path = tmp_path / "events.db"
    store = SQLiteEventStore(path)
    event = generate_customer_journey(seed=42)[0]

    assert store.insert_event(event) is True
    assert store.count_events() == 1

    retrieved = store.get_event(event.event_id)
    assert retrieved is not None
    assert retrieved.event_id == event.event_id
    assert retrieved.event_name == event.event_name
    assert retrieved.ingested_at is not None


def test_sqlite_duplicate_protection(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    event = generate_customer_journey(seed=42)[0]

    assert store.insert_event(event) is True
    assert store.insert_event(event) is False
    assert store.count_events() == 1


def test_sqlite_survives_reopening(tmp_path):
    path = tmp_path / "events.db"
    event = generate_customer_journey(seed=42)[0]

    first_store = SQLiteEventStore(path)
    first_store.insert_event(event)

    reopened_store = SQLiteEventStore(path)

    assert reopened_store.count_events() == 1
    assert reopened_store.get_event(event.event_id) is not None


def test_api_persists_event_and_detects_duplicate(tmp_path):
    store = SQLiteEventStore(tmp_path / "api.db")
    app.dependency_overrides[get_event_store] = lambda: store

    try:
        with TestClient(app) as client:
            event = generate_customer_journey(seed=42)[0]
            payload = event.model_dump(mode="json")

            first = client.post("/v1/events", json=payload)
            second = client.post("/v1/events", json=payload)

            assert first.status_code == 202
            assert first.json()["status"] == "stored"

            assert second.status_code == 202
            assert second.json()["status"] == "duplicate"

            assert store.count_events() == 1
    finally:
        app.dependency_overrides.clear()
