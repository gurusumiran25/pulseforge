import pytest
from fastapi.testclient import TestClient

from services.generator.journey_generator import generate_customer_journey
from services.ingestion.main import app, get_event_store
from services.storage.sqlite_store import SQLiteEventStore


@pytest.fixture
def batch_client(tmp_path):
    store = SQLiteEventStore(tmp_path / "batch_test.db")
    app.dependency_overrides[get_event_store] = lambda: store

    try:
        with TestClient(app) as client:
            yield client, store
    finally:
        app.dependency_overrides.pop(get_event_store, None)


def test_batch_stores_multiple_events(batch_client):
    client, store = batch_client
    events = generate_customer_journey(seed=42)
    payload = [event.model_dump(mode="json") for event in events]

    response = client.post("/v1/events/batch", json=payload)

    assert response.status_code == 202
    assert response.json() == {
        "status": "processed",
        "received": len(events),
        "inserted": len(events),
        "duplicates": 0,
    }
    assert store.count_events() == len(events)


def test_batch_detects_duplicates(batch_client):
    client, store = batch_client
    events = generate_customer_journey(seed=42)
    payload = [event.model_dump(mode="json") for event in events]

    first = client.post("/v1/events/batch", json=payload)
    second = client.post("/v1/events/batch", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["inserted"] == 0
    assert second.json()["duplicates"] == len(events)
    assert store.count_events() == len(events)


def test_empty_batch_rejected(batch_client):
    client, _ = batch_client

    response = client.post("/v1/events/batch", json=[])

    assert response.status_code == 422


def test_invalid_batch_rejected(batch_client):
    client, store = batch_client
    events = generate_customer_journey(seed=42)
    payload = [event.model_dump(mode="json") for event in events]
    payload[1]["schema_version"] = 99

    response = client.post("/v1/events/batch", json=payload)

    assert response.status_code == 422
    assert store.count_events() == 0


def test_oversized_batch_rejected(batch_client):
    client, store = batch_client
    event = generate_customer_journey(seed=42)[0]
    payload = [event.model_dump(mode="json") for _ in range(1001)]

    response = client.post("/v1/events/batch", json=payload)

    assert response.status_code == 422
    assert store.count_events() == 0
