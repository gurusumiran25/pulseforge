import argparse
import base64
import json
import logging

from confluent_kafka import Consumer, KafkaException, Producer
from pydantic import ValidationError

from contracts.event_validation import EventEnvelope
from services.storage.sqlite_store import SQLiteEventStore


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


class PulseForgeConsumer:
    def __init__(
        self,
        bootstrap_servers="127.0.0.1:19092",
        topic="pulseforge.events.v1",
        group_id="pulseforge-sqlite-consumer-v1",
        db_path="data/storage/pulseforge.db",
        offset_reset="earliest",
        dlq_topic="pulseforge.events.dlq.v1",
    ):
        self.topic = topic
        self.dlq_topic = dlq_topic
        self.dlq_producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "acks": "all",
            "enable.idempotence": True,
        })
        self.store = SQLiteEventStore(db_path)

        self.consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": offset_reset,
            "enable.auto.commit": False,
            "enable.auto.offset.store": False,
        })

    def _commit_checked(self, message):
        committed_partitions = self.consumer.commit(
            message=message,
            asynchronous=False,
        )
        if not committed_partitions:
            raise RuntimeError("Kafka returned no offset commit result")
        for partition in committed_partitions:
            if partition.error is not None:
                raise RuntimeError(
                    f"Kafka offset commit failed: {partition.error}"
                )

    def _publish_to_dlq(self, message, error):
        payload = {
            "original_topic": message.topic(),
            "original_partition": message.partition(),
            "original_offset": message.offset(),
            "error": str(error),
            "raw_value_base64": base64.b64encode(
                message.value() or b""
            ).decode("ascii"),
        }

        delivery = {"confirmed": False, "error": None}

        def on_delivery(err, record):
            delivery["error"] = err
            delivery["confirmed"] = err is None

        self.dlq_producer.produce(
            topic=self.dlq_topic,
            key=f"{message.topic()}:{message.partition()}:{message.offset()}",
            value=json.dumps(payload).encode("utf-8"),
            on_delivery=on_delivery,
        )

        remaining = self.dlq_producer.flush(timeout=15)
        if remaining != 0 or not delivery["confirmed"]:
            raise RuntimeError(
                f"DLQ delivery failed: {delivery['error'] or 'not confirmed'}"
            )

    def process_message(self, message):
        if message.error():
            raise KafkaException(message.error())

        try:
            event = EventEnvelope.model_validate_json(message.value())
        except (ValidationError, ValueError, TypeError) as exc:
            logger.error(
                "Invalid event at partition=%s offset=%s: %s",
                message.partition(),
                message.offset(),
                exc,
            )
            self._publish_to_dlq(message, exc)
            self._commit_checked(message)
            logger.warning("Invalid event safely routed to DLQ")
            return "dlq"

        inserted = self.store.insert_event(event)

        # SQLite transaction has committed before this point.
        # Commit the next offset only after successful persistence.
        self._commit_checked(message)

        status = "inserted" if inserted else "duplicate"

        logger.info(
            "Event %s: %s | partition=%s offset=%s",
            status,
            event.event_id,
            message.partition(),
            message.offset(),
        )

        return status

    def run(self, max_messages=None):
        processed = 0
        self.consumer.subscribe([self.topic])

        logger.info("Consumer subscribed to %s", self.topic)

        try:
            while max_messages is None or processed < max_messages:
                message = self.consumer.poll(timeout=1.0)

                if message is None:
                    continue

                status = self.process_message(message)

                processed += 1

        except KeyboardInterrupt:
            logger.info("Consumer stopped by user")
        finally:
            self.consumer.close()

        return processed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-messages", type=int, default=None)
    parser.add_argument(
        "--group-id",
        default="pulseforge-sqlite-consumer-v1",
    )
    parser.add_argument(
        "--db-path",
        default="data/storage/pulseforge.db",
    )
    args = parser.parse_args()

    consumer = PulseForgeConsumer(
        group_id=args.group_id,
        db_path=args.db_path,
    )
    consumer.run(max_messages=args.max_messages)


if __name__ == "__main__":
    main()
