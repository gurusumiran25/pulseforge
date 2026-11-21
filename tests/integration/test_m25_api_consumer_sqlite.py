"""M25 API -> producer contract -> consumer -> SQLite -> Silver/Gold.

This is a deterministic in-process boundary test using an in-memory broker
double. It does NOT claim real Redpanda network integration.
"""
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from services.generator.journey_generator import generate_customer_journey
from services.ingestion.main import app, get_event_producer
from services.streaming.consumer import PulseForgeConsumer
from services.storage.sqlite_store import SQLiteEventStore


VIEWS = Path(__file__).resolve().parents[2] / "warehouse/sql/m20_views.sql"


class BrokerDouble:
    def __init__(self):
        self.published = []

    def publish(self, event):
        self.published.append(event.model_dump_json().encode("utf-8"))
        return event.event_id


class MessageDouble:
    def __init__(self, payload, offset):
        self.payload = payload
        self._offset = offset

    def error(self):
        return None

    def value(self):
        return self.payload

    def partition(self):
        return 0

    def offset(self):
        return self._offset


class ConsumerCommitDouble:
    def __init__(self):
        self.committed = []

    def commit(self, message, asynchronous=False):
        self.committed.append(message.offset())
        return [SimpleNamespace(error=None)]


def test_api_batch_to_consumer_to_warehouse(tmp_path):
    broker = BrokerDouble()
    app.dependency_overrides[get_event_producer] = lambda: broker
    try:
        journey = generate_customer_journey(seed=42)
        with TestClient(app) as client:
            response = client.post(
                "/v1/events/batch",
                json=[event.model_dump(mode="json") for event in journey],
            )
        assert response.status_code == 202, response.text
        assert response.json()["published"] == len(journey)
    finally:
        app.dependency_overrides.clear()

    assert len(broker.published) == len(journey)
    store = SQLiteEventStore(tmp_path / "events.db")

    # Construct the consumer without starting a real Kafka connection.
    consumer = PulseForgeConsumer.__new__(PulseForgeConsumer)
    consumer.store = store
    consumer.consumer = ConsumerCommitDouble()

    for offset, payload in enumerate(broker.published):
        assert consumer.process_message(MessageDouble(payload, offset)) == "inserted"
    assert consumer.consumer.committed == list(range(len(journey)))

    with store.connect() as connection:
        connection.executescript(VIEWS.read_text(encoding="utf-8"))
        silver = connection.execute("select count(*) from silver_events").fetchone()[0]
        session = connection.execute(
            "select event_count, viewed_product from gold_session_funnel"
        ).fetchone()
    assert silver == len(journey)
    assert session["event_count"] == len(journey)
    assert session["viewed_product"] == 1

    # Replay the exact broker payloads to verify idempotency at the storage boundary.
    for offset, payload in enumerate(broker.published, start=len(journey)):
        assert consumer.process_message(MessageDouble(payload, offset)) == "duplicate"
    assert store.count_events() == len(journey)
    assert consumer.consumer.committed == list(range(len(journey) * 2))
