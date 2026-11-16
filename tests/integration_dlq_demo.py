import base64
import json
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from confluent_kafka import Consumer, Producer

from contracts.event_validation import EventEnvelope
from services.streaming.consumer import PulseForgeConsumer

BROKER = "127.0.0.1:19092"
TEST_TOPIC = "pulseforge.events.test.v1"
DLQ_TOPIC = "pulseforge.events.dlq.v1"

run_id = uuid.uuid4().hex
invalid_payload = b'{"event_id":"invalid-dlq-test"}'

valid_event = EventEnvelope(
    event_id=f"dlq-valid-{run_id}",
    event_name="page_view",
    schema_version=1,
    event_time=datetime.now(timezone.utc),
    user_id="dlq-test-user",
    session_id=f"dlq-session-{run_id}",
    source="integration-test",
    platform="web",
    properties={"page_path": "/dlq-test"},
)

producer = Producer({
    "bootstrap.servers": BROKER,
    "acks": "all",
})

delivery_errors = []

def delivery_callback(error, message):
    if error is not None:
        delivery_errors.append(str(error))

producer.produce(
    TEST_TOPIC,
    key=f"dlq-session-{run_id}",
    value=invalid_payload,
    on_delivery=delivery_callback,
)
producer.produce(
    TEST_TOPIC,
    key=f"dlq-session-{run_id}",
    value=valid_event.model_dump_json().encode("utf-8"),
    on_delivery=delivery_callback,
)

remaining = producer.flush(15)
if remaining or delivery_errors:
    raise RuntimeError(
        f"Test publication failed: {delivery_errors}, remaining={remaining}"
    )

print("Published invalid and valid events.")
print("Run ID:", run_id)

with tempfile.TemporaryDirectory() as temp_dir:
    db_path = Path(temp_dir) / "dlq_integration.db"

    consumer = PulseForgeConsumer(
        bootstrap_servers=BROKER,
        topic=TEST_TOPIC,
        group_id=f"pulseforge-dlq-integration-{run_id}",
        db_path=db_path,
    )

    # The test topic may contain earlier messages. Find our two events
    # by polling until both are observed, with a bounded timeout.
    import time
    consumer.consumer.subscribe([TEST_TOPIC])
    found_valid = False
    found_invalid = False
    deadline = time.monotonic() + 45

    try:
        while time.monotonic() < deadline:
            message = consumer.consumer.poll(1)
            if message is None:
                continue
            if message.error():
                raise RuntimeError(str(message.error()))

            raw = message.value()
            if raw == invalid_payload:
                found_invalid = True
                status = consumer.process_message(message)
                assert status == "dlq", status
            elif valid_event.event_id.encode() in raw:
                found_valid = True
                status = consumer.process_message(message)
                assert status == "inserted", status
            else:
                # Earlier records are intentionally not processed.
                continue

            if found_valid and found_invalid:
                break
    finally:
        consumer.consumer.close()

    assert found_invalid, "Invalid event was not consumed"
    assert found_valid, "Valid event was not consumed"
    assert consumer.store.count_events() == 1

    print("PASS: Invalid event routed to DLQ.")
    print("PASS: Valid event persisted to SQLite.")

dlq_reader = Consumer({
    "bootstrap.servers": BROKER,
    "group.id": f"pulseforge-dlq-reader-{run_id}",
    "auto.offset.reset": "earliest",
})
dlq_reader.subscribe([DLQ_TOPIC])

import time
deadline = time.monotonic() + 45
matched = False

try:
    while time.monotonic() < deadline:
        message = dlq_reader.poll(1)
        if message is None:
            continue
        if message.error():
            raise RuntimeError(str(message.error()))

        record = json.loads(message.value())
        if (
            record.get("original_topic") == TEST_TOPIC
            and record.get("raw_value_base64")
            == base64.b64encode(invalid_payload).decode("ascii")
        ):
            matched = True
            print("PASS: Original invalid payload verified in DLQ.")
            print("DLQ record:", json.dumps(record, indent=2))
            break
finally:
    dlq_reader.close()

assert matched, "Matching DLQ record not found"
print("SUCCESS: Real Redpanda DLQ integration test passed.")
