import json

from confluent_kafka import Producer
from contracts.event_validation import EventEnvelope


class PulseForgeProducer:
    def __init__(
        self,
        bootstrap_servers="127.0.0.1:19092",
        topic="pulseforge.events.v1",
    ):
        self.topic = topic
        self.producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "client.id": "pulseforge-producer",
            "acks": "all",
            "enable.idempotence": True,
        })

    def publish(self, event: EventEnvelope):
        payload = event.model_dump(mode="json")
        delivery = {"confirmed": False, "error": None}

        def on_delivery(error, message):
            if error is not None:
                delivery["error"] = str(error)
            else:
                delivery["confirmed"] = True

        self.producer.produce(
            topic=self.topic,
            key=event.session_id.encode("utf-8"),
            value=json.dumps(payload).encode("utf-8"),
            on_delivery=on_delivery,
        )

        remaining = self.producer.flush(timeout=10)

        if delivery["error"] is not None:
            raise RuntimeError(
                f"Kafka delivery failed: {delivery['error']}"
            )

        if remaining or not delivery["confirmed"]:
            raise RuntimeError(
                "Kafka delivery was not confirmed within 10 seconds"
            )

        return event.event_id
