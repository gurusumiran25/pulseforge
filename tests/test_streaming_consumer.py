from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from contracts.event_validation import EventEnvelope
from services.streaming.consumer import PulseForgeConsumer


@pytest.fixture
def consumer(tmp_path):
    with (
        patch("services.streaming.consumer.Consumer") as mock_consumer_class,
        patch("services.streaming.consumer.Producer") as mock_producer_class,
    ):
        mock_kafka = MagicMock()
        mock_producer = MagicMock()
        mock_producer_class.return_value = mock_producer

        def successful_delivery(*args, **kwargs):
            callback = kwargs["on_delivery"]
            callback(None, MagicMock())

        mock_producer.produce.side_effect = successful_delivery
        mock_producer.flush.return_value = 0

        successful_partition = MagicMock()
        successful_partition.error = None
        mock_kafka.commit.return_value = [successful_partition]
        mock_consumer_class.return_value = mock_kafka

        instance = PulseForgeConsumer(
            topic="pulseforge.events.test.v1",
            group_id="pulseforge-unit-test",
            db_path=tmp_path / "streaming_test.db",
        )

        yield instance

        instance.consumer.close()


def make_event(event_id="stream-test-001"):
    return EventEnvelope(
        event_id=event_id,
        event_name="page_view",
        schema_version=1,
        event_time=datetime.now(timezone.utc),
        user_id="test-user",
        session_id="test-session",
        source="pytest",
        platform="web",
        properties={"page_path": "/products"},
    )


def make_message(event):
    message = MagicMock()
    message.error.return_value = None
    message.value.return_value = event.model_dump_json().encode("utf-8")
    message.partition.return_value = 0
    message.offset.return_value = 0
    return message


def test_consumer_inserts_valid_event(consumer):
    event = make_event()
    message = make_message(event)

    result = consumer.process_message(message)

    assert result == "inserted"
    assert consumer.store.count_events() == 1

    consumer.consumer.commit.assert_called_once_with(
        message=message,
        asynchronous=False,
    )


def test_consumer_detects_duplicate(consumer):
    event = make_event()
    message = make_message(event)

    first = consumer.process_message(message)
    second = consumer.process_message(message)

    assert first == "inserted"
    assert second == "duplicate"
    assert consumer.store.count_events() == 1
    assert consumer.consumer.commit.call_count == 2


def make_invalid_message():
    message = MagicMock()
    message.error.return_value = None
    message.value.return_value = b'{"event_id":"invalid"}'
    message.topic.return_value = "pulseforge.events.test.v1"
    message.partition.return_value = 0
    message.offset.return_value = 12
    return message


def test_invalid_event_sent_to_dlq_and_committed(consumer):
    message = make_invalid_message()

    result = consumer.process_message(message)

    assert result == "dlq"
    assert consumer.store.count_events() == 0
    consumer.dlq_producer.produce.assert_called_once()
    consumer.dlq_producer.flush.assert_called_once()
    consumer.consumer.commit.assert_called_once_with(
        message=message,
        asynchronous=False,
    )


def test_dlq_delivery_failure_does_not_commit(consumer):
    message = make_invalid_message()

    consumer.dlq_producer.flush.return_value = 1

    with pytest.raises(RuntimeError, match="DLQ delivery failed"):
        consumer.process_message(message)

    consumer.consumer.commit.assert_not_called()


def test_dlq_callback_failure_does_not_commit(consumer):
    message = make_invalid_message()

    def failed_delivery(*args, **kwargs):
        kwargs["on_delivery"]("simulated broker error", MagicMock())

    consumer.dlq_producer.produce.side_effect = failed_delivery

    with pytest.raises(RuntimeError, match="DLQ delivery failed"):
        consumer.process_message(message)

    consumer.consumer.commit.assert_not_called()


def test_dlq_commit_failure_raises(consumer):
    message = make_invalid_message()

    failed_partition = MagicMock()
    failed_partition.error = "simulated commit failure"
    consumer.consumer.commit.return_value = [failed_partition]

    with pytest.raises(RuntimeError, match="Kafka offset commit failed"):
        consumer.process_message(message)

    consumer.dlq_producer.produce.assert_called_once()




def test_consumer_raises_on_commit_failure(consumer):
    event = make_event("commit-failure-001")
    message = make_message(event)

    failed_partition = MagicMock()
    failed_partition.error = "simulated commit failure"
    consumer.consumer.commit.return_value = [failed_partition]

    with pytest.raises(RuntimeError, match="Kafka offset commit failed"):
        consumer.process_message(message)

    assert consumer.store.count_events() == 1
