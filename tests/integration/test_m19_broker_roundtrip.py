"""Opt-in, isolated Redpanda integration tests for PulseForge M19.

These tests never use the default application topics, consumer group or DB.
They require explicit opt-in and a loopback-only Kafka endpoint.
"""
import base64
import json
import os
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic

from contracts.event_validation import EventEnvelope
from services.streaming.consumer import PulseForgeConsumer
from services.streaming.producer import PulseForgeProducer


ENABLED = os.getenv("PULSEFORGE_RUN_BROKER_TESTS") == "1"
BOOTSTRAP = os.getenv("PULSEFORGE_TEST_BOOTSTRAP", "127.0.0.1:19093")
ISOLATED_ENDPOINTS = {"127.0.0.1:19093", "localhost:19093"}

pytestmark = pytest.mark.skipif(
    not ENABLED, reason="Explicit opt-in required: PULSEFORGE_RUN_BROKER_TESTS=1"
)


def _receive(consumer, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        msg = consumer.poll(0.5)
        if msg is None:
            continue
        if msg.error():
            raise RuntimeError(str(msg.error()))
        return msg
    pytest.fail("Timed out waiting for isolated broker message")


@pytest.fixture
def broker_resources(tmp_path):
    if BOOTSTRAP not in ISOLATED_ENDPOINTS:
        pytest.fail("M19 tests require the dedicated loopback broker on port 19093")

    suffix = uuid4().hex
    topic = f"pulseforge.m19.test.{suffix}"
    dlq = f"pulseforge.m19.dlq.{suffix}"
    group = f"pulseforge-m19-test-{suffix}"
    admin = AdminClient({"bootstrap.servers": BOOTSTRAP})

    # The only broker resources created are UUID-scoped test topics.
    futures = admin.create_topics(
        [NewTopic(topic, num_partitions=1, replication_factor=1),
         NewTopic(dlq, num_partitions=1, replication_factor=1)],
        operation_timeout=10,
    )
    for future in futures.values():
        future.result(timeout=15)

    try:
        yield {
            "topic": topic,
            "dlq": dlq,
            "group": group,
            "db_path": tmp_path / "m19_isolated_events.db",
        }
    finally:
        # Never delete shared or pre-existing topics. These names are unique
        # to this fixture; cleanup failures are non-destructive but visible.
        futures = admin.delete_topics([topic, dlq], operation_timeout=10)
        for name, future in futures.items():
            try:
                future.result(timeout=15)
            except Exception as exc:
                pytest.fail(f"Unable to remove isolated topic {name}: {exc}")


def _event():
    return EventEnvelope(
        event_id=f"m19-{uuid4().hex}",
        event_name="page_view",
        schema_version=1,
        event_time=datetime.now(timezone.utc),
        user_id="m19-synthetic-user",
        session_id=f"m19-session-{uuid4().hex}",
        source="m19-integration-test",
        platform="web",
        properties={"page_path": "/m19-test"},
    )


def _test_consumer(resources):
    return PulseForgeConsumer(
        bootstrap_servers=BOOTSTRAP,
        topic=resources["topic"],
        dlq_topic=resources["dlq"],
        group_id=resources["group"],
        db_path=resources["db_path"],
        offset_reset="earliest",
    )


def test_valid_event_roundtrip_and_duplicate_storage(broker_resources):
    resources = broker_resources
    event = _event()
    producer = PulseForgeProducer(
        bootstrap_servers=BOOTSTRAP, topic=resources["topic"]
    )
    consumer = _test_consumer(resources)
    consumer.consumer.subscribe([resources["topic"]])
    try:
        assert producer.publish(event) == event.event_id
        first = _receive(consumer.consumer)
        assert consumer.process_message(first) == "inserted"
        assert consumer.store.count_events() == 1
        assert consumer.store.get_event(event.event_id).event_id == event.event_id

        # A separate successful publication of the same event ID must
        # not create a second stored event.
        producer.publish(event)
        second = _receive(consumer.consumer)
        assert consumer.process_message(second) == "duplicate"
        assert consumer.store.count_events() == 1
    finally:
        consumer.consumer.close()


def test_invalid_event_goes_to_dlq_without_storage(broker_resources):
    resources = broker_resources
    invalid = b'{"event_id":"incomplete-m19-event"}'
    producer = Producer({"bootstrap.servers": BOOTSTRAP, "acks": "all"})
    consumer = _test_consumer(resources)
    observer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": f"{resources['group']}-dlq-observer",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.consumer.subscribe([resources["topic"]])
    observer.subscribe([resources["dlq"]])
    try:
        producer.produce(resources["topic"], value=invalid)
        assert producer.flush(10) == 0
        message = _receive(consumer.consumer)
        assert consumer.process_message(message) == "dlq"
        assert consumer.store.count_events() == 0

        dlq_message = _receive(observer)
        payload = json.loads(dlq_message.value())
        assert payload["original_topic"] == resources["topic"]
        assert payload["original_offset"] == message.offset()
        assert base64.b64decode(payload["raw_value_base64"]) == invalid
    finally:
        observer.close()
        consumer.consumer.close()


def test_restart_replays_uncommitted_event_without_duplicate_row(
    broker_resources, monkeypatch
):
    """Persist event, simulate failed offset commit, restart same group."""
    resources = broker_resources
    event = _event()
    producer = PulseForgeProducer(
        bootstrap_servers=BOOTSTRAP, topic=resources["topic"]
    )
    first_consumer = _test_consumer(resources)
    first_consumer.consumer.subscribe([resources["topic"]])
    try:
        assert producer.publish(event) == event.event_id
        first_message = _receive(first_consumer.consumer)
        first_offset = first_message.offset()

        def fail_commit(_message):
            raise RuntimeError("simulated offset commit failure")

        # Only the offset commit is injected; actual broker delivery and
        # SQLite persistence remain real.
        with monkeypatch.context() as patcher:
            patcher.setattr(first_consumer, "_commit_checked", fail_commit)
            with pytest.raises(RuntimeError, match="simulated offset commit"):
                first_consumer.process_message(first_message)

        assert first_consumer.store.count_events() == 1
    finally:
        first_consumer.consumer.close()

    # Same consumer group and same SQLite database after restart.
    restarted = _test_consumer(resources)
    restarted.consumer.subscribe([resources["topic"]])
    try:
        replay = _receive(restarted.consumer)
        assert replay.offset() == first_offset
        assert restarted.process_message(replay) == "duplicate"
        assert restarted.store.count_events() == 1
        assert restarted.store.get_event(event.event_id).event_id == event.event_id
    finally:
        restarted.consumer.close()


def test_restart_replays_invalid_event_after_failed_dlq_commit(
    broker_resources, monkeypatch
):
    """DLQ delivery may repeat when source offset was not committed."""
    resources = broker_resources
    invalid = b'{"event_id":"incomplete-replay-event"}'
    producer = Producer({"bootstrap.servers": BOOTSTRAP, "acks": "all"})
    first_consumer = _test_consumer(resources)
    first_consumer.consumer.subscribe([resources["topic"]])
    try:
        producer.produce(resources["topic"], value=invalid)
        assert producer.flush(10) == 0
        first_message = _receive(first_consumer.consumer)
        first_offset = first_message.offset()

        def fail_commit(_message):
            raise RuntimeError("simulated DLQ offset commit failure")

        with monkeypatch.context() as patcher:
            patcher.setattr(first_consumer, "_commit_checked", fail_commit)
            with pytest.raises(RuntimeError, match="simulated DLQ offset"):
                first_consumer.process_message(first_message)

        assert first_consumer.store.count_events() == 0
    finally:
        first_consumer.consumer.close()

    restarted = _test_consumer(resources)
    restarted.consumer.subscribe([resources["topic"]])
    observer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": f"{resources['group']}-replay-observer",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    observer.subscribe([resources["dlq"]])
    try:
        replay = _receive(restarted.consumer)
        assert replay.offset() == first_offset
        assert restarted.process_message(replay) == "dlq"
        assert restarted.store.count_events() == 0

        # The two DLQ records represent the same source offset. This
        # documents at-least-once DLQ publication, not exactly-once.
        first_dlq = json.loads(_receive(observer).value())
        second_dlq = json.loads(_receive(observer).value())
        for record in (first_dlq, second_dlq):
            assert record["original_topic"] == resources["topic"]
            assert record["original_offset"] == first_offset
            assert base64.b64decode(record["raw_value_base64"]) == invalid
    finally:
        observer.close()
        restarted.consumer.close()
