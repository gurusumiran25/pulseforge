"""M26 real Redpanda broker test: FastAPI -> Kafka -> consumer -> SQLite -> SQL.

Requires M26_KAFKA_BOOTSTRAP to be set by the dedicated CI workflow.
Never accesses the operational SQLite database.
"""
import os
import time
from pathlib import Path
from uuid import uuid4

import pytest
from confluent_kafka.admin import AdminClient, NewTopic
from fastapi.testclient import TestClient

from services.generator.journey_generator import generate_customer_journey
from services.ingestion.main import app, get_event_producer
from services.streaming.producer import PulseForgeProducer
from services.streaming.consumer import PulseForgeConsumer


VIEWS = Path(__file__).resolve().parents[2] / "warehouse/sql/m20_views.sql"


@pytest.mark.skipif(not os.environ.get("M26_KAFKA_BOOTSTRAP"), reason="Real broker only in dedicated M26 CI")
def test_api_real_redpanda_consumer_sqlite_warehouse(tmp_path):
    bootstrap = os.environ["M26_KAFKA_BOOTSTRAP"]
    suffix = uuid4().hex[:10]
    topic = f"pulseforge.m26.{suffix}"
    dlq_topic = f"pulseforge.m26.dlq.{suffix}"
    admin = AdminClient({"bootstrap.servers": bootstrap})
    futures = admin.create_topics([
        NewTopic(topic, num_partitions=1, replication_factor=1),
        NewTopic(dlq_topic, num_partitions=1, replication_factor=1),
    ])
    for future in futures.values():
        future.result(timeout=30)

    producer = PulseForgeProducer(bootstrap_servers=bootstrap, topic=topic)
    app.dependency_overrides[get_event_producer] = lambda: producer
    journey = generate_customer_journey(seed=42)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/events/batch",
                json=[event.model_dump(mode="json") for event in journey],
            )
        assert response.status_code == 202, response.text
        assert response.json()["published"] == len(journey)
    finally:
        app.dependency_overrides.clear()

    consumer = PulseForgeConsumer(
        bootstrap_servers=bootstrap,
        topic=topic,
        dlq_topic=dlq_topic,
        group_id=f"m26-{suffix}",
        db_path=tmp_path / "m26-events.db",
        offset_reset="earliest",
    )
    processed = 0
    deadline = time.monotonic() + 45
    try:
        consumer.consumer.subscribe([topic])
        while processed < len(journey) and time.monotonic() < deadline:
            message = consumer.consumer.poll(timeout=1.0)
            if message is None:
                continue
            assert consumer.process_message(message) == "inserted"
            processed += 1
    finally:
        consumer.consumer.close()
        consumer.dlq_producer.flush(5)

    assert processed == len(journey), f"Only received {processed}/{len(journey)} broker events"
    assert consumer.store.count_events() == len(journey)
    with consumer.store.connect() as connection:
        connection.executescript(VIEWS.read_text(encoding="utf-8"))
        assert connection.execute("select count(*) from silver_events").fetchone()[0] == len(journey)
        row = connection.execute(
            "select event_count, viewed_product from gold_session_funnel"
        ).fetchone()
        assert row["event_count"] == len(journey)
        assert row["viewed_product"] == 1
