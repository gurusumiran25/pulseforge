import tempfile
import time
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from contracts.event_validation import EventEnvelope
from services.ingestion.main import app, get_event_producer
from services.streaming.consumer import PulseForgeConsumer
from services.streaming.producer import PulseForgeProducer
from services.storage.sqlite_store import SQLiteEventStore

from datetime import datetime, timezone

BROKER = "127.0.0.1:19092"
TOPIC = "pulseforge.events.test.v1"

run_id = uuid.uuid4().hex
event = EventEnvelope(
    event_id=f"e2e-{run_id}",
    event_name="page_view",
    schema_version=1,
    event_time=datetime.now(timezone.utc),
    user_id=f"user-{run_id}",
    session_id=f"session-{run_id}",
    source="e2e-integration-test",
    platform="web",
    properties={"page_path": "/pulseforge-e2e"},
)

with tempfile.TemporaryDirectory() as directory:
    db_path = Path(directory) / "e2e.db"

    consumer = PulseForgeConsumer(
        bootstrap_servers=BROKER,
        topic=TOPIC,
        group_id=f"pulseforge-e2e-{run_id}",
        db_path=db_path,
        offset_reset="earliest",
    )

    producer = PulseForgeProducer(
        bootstrap_servers=BROKER,
        topic=TOPIC,
    )

    # Override only the API producer dependency.
    app.dependency_overrides[get_event_producer] = lambda: producer

    try:
        consumer.consumer.subscribe([TOPIC])

        with TestClient(app) as client:
            response = client.post(
                "/v1/events",
                json=event.model_dump(mode="json"),
            )

        print("HTTP status:", response.status_code)
        print("HTTP response:", response.json())

        assert response.status_code == 202
        assert response.json()["status"] == "accepted"
        assert response.json()["event_id"] == event.event_id

        print("PASS: FastAPI accepted event after Kafka delivery.")

        deadline = time.monotonic() + 60
        matched = False

        while time.monotonic() < deadline:
            message = consumer.consumer.poll(1.0)

            if message is None:
                continue

            if message.error():
                raise RuntimeError(str(message.error()))

            # The shared test topic may contain older records.
            # Only process the unique event from this run.
            try:
                received = EventEnvelope.model_validate_json(
                    message.value()
                )
            except Exception:
                continue

            if received.event_id != event.event_id:
                continue

            status = consumer.process_message(message)
            assert status == "inserted", status
            matched = True
            break

        assert matched, "Timed out waiting for the matching Kafka event"

        store = SQLiteEventStore(db_path)
        stored = store.get_event(event.event_id)

        assert stored is not None
        assert stored.event_id == event.event_id
        assert stored.event_name == event.event_name
        assert store.count_events() == 1

        print("PASS: Consumer received event from Redpanda.")
        print("PASS: Event persisted in SQLite.")
        print("PASS: Kafka offset commit completed.")
        print("SUCCESS: End-to-end pipeline integration passed.")

    finally:
        app.dependency_overrides.pop(get_event_producer, None)
        consumer.consumer.close()
