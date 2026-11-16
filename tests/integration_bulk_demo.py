"""Offline bulk ingestion integration demo.

Uses FastAPI's TestClient and a mocked Kafka producer.
No real broker connection or production database access.
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from services.generator.journey_generator import generate_customer_journey
from services.ingestion.main import app, get_event_producer


def main():
    events = generate_customer_journey(seed=42)
    payload = [event.model_dump(mode="json") for event in events]

    producer = MagicMock()
    app.dependency_overrides[get_event_producer] = lambda: producer

    try:
        with TestClient(app) as client:
            response = client.post("/v1/events/batch", json=payload)

        response.raise_for_status()
        result = response.json()

        assert result["status"] == "accepted"
        assert result["received"] == len(events)
        assert result["published"] == len(events)
        assert producer.publish.call_count == len(events)

        print("Dataset events:", len(events))
        print("Accepted:", result["received"])
        print("Mock publications:", producer.publish.call_count)
        print("PASS: Offline bulk ingestion demo")

    finally:
        app.dependency_overrides.pop(get_event_producer, None)


if __name__ == "__main__":
    main()
