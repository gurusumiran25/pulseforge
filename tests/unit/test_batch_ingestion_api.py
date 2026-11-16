from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from services.generator.journey_generator import generate_customer_journey
from services.ingestion.main import app, get_event_producer


@pytest.fixture
def batch_client():
    producer = MagicMock()
    app.dependency_overrides[get_event_producer] = lambda: producer

    try:
        with TestClient(app) as client:
            yield client, producer
    finally:
        app.dependency_overrides.pop(get_event_producer, None)


def make_payload():
    events = generate_customer_journey(seed=42)
    return events, [event.model_dump(mode="json") for event in events]


def test_batch_publishes_multiple_events(batch_client):
    client, producer = batch_client
    events, payload = make_payload()

    response = client.post("/v1/events/batch", json=payload)

    assert response.status_code == 202
    assert response.json() == {
        "status": "accepted",
        "received": len(events),
        "published": len(events),
    }
    assert producer.publish.call_count == len(events)


def test_batch_replay_publishes_again(batch_client):
    client, producer = batch_client
    events, payload = make_payload()

    first = client.post("/v1/events/batch", json=payload)
    second = client.post("/v1/events/batch", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["published"] == len(events)
    assert producer.publish.call_count == 2 * len(events)


def test_empty_batch_rejected(batch_client):
    client, producer = batch_client

    response = client.post("/v1/events/batch", json=[])

    assert response.status_code == 422
    producer.publish.assert_not_called()


def test_invalid_batch_rejected(batch_client):
    client, producer = batch_client
    _, payload = make_payload()
    payload[1]["schema_version"] = 99

    response = client.post("/v1/events/batch", json=payload)

    assert response.status_code == 422
    producer.publish.assert_not_called()


def test_oversized_batch_rejected(batch_client):
    client, producer = batch_client
    _, payload = make_payload()

    response = client.post(
        "/v1/events/batch",
        json=[payload[0] for _ in range(1001)],
    )

    assert response.status_code == 422
    producer.publish.assert_not_called()


def test_batch_partial_failure_returns_503(batch_client):
    client, producer = batch_client
    _, payload = make_payload()

    def publish_with_failure(event):
        if producer.publish.call_count == 2:
            raise RuntimeError("simulated Kafka failure")
        return event.event_id

    producer.publish.side_effect = publish_with_failure

    response = client.post("/v1/events/batch", json=payload)

    assert response.status_code == 503
    assert response.json()["detail"]["confirmed"] == 1
    assert response.json()["detail"]["requested"] == len(payload)


def test_batch_first_publication_failure_returns_503(batch_client):
    client, producer = batch_client
    _, payload = make_payload()
    producer.publish.side_effect = RuntimeError("Kafka unavailable")

    response = client.post("/v1/events/batch", json=payload)

    assert response.status_code == 503
    assert response.json()["detail"]["confirmed"] == 0
