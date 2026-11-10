from fastapi.testclient import TestClient

from services.generator.journey_generator import generate_customer_journey
from services.ingestion.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "pulseforge-ingestion",
    }


def test_valid_event_is_accepted():
    event = generate_customer_journey(seed=42)[0]

    response = client.post(
        "/v1/events",
        json=event.model_dump(mode="json"),
    )

    assert response.status_code == 202

    body = response.json()
    assert body["status"] == "stored"
    assert body["event_id"] == event.event_id
    assert body["event_name"] == "page_view"
    assert "received_at" in body


def test_invalid_schema_version_is_rejected():
    event = generate_customer_journey(seed=42)[0]
    payload = event.model_dump(mode="json")
    payload["schema_version"] = 99

    response = client.post("/v1/events", json=payload)

    assert response.status_code == 422


def test_missing_required_property_is_rejected():
    event = generate_customer_journey(seed=42)[0]
    payload = event.model_dump(mode="json")
    payload["properties"] = {}

    response = client.post("/v1/events", json=payload)

    assert response.status_code == 422


def test_missing_event_id_is_rejected():
    event = generate_customer_journey(seed=42)[0]
    payload = event.model_dump(mode="json")
    del payload["event_id"]

    response = client.post("/v1/events", json=payload)

    assert response.status_code == 422
