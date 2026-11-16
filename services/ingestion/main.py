import logging
from datetime import datetime, timezone

from fastapi import Body, Depends, FastAPI, HTTPException

from contracts.event_validation import EventEnvelope
from services.streaming.producer import PulseForgeProducer


logger = logging.getLogger(__name__)

app = FastAPI(
    title="PulseForge Event Ingestion API",
    version="0.4.0",
    description="Validated product analytics ingestion through Redpanda",
)


def get_event_producer():
    return PulseForgeProducer()


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "pulseforge-ingestion"}


@app.post("/v1/events", status_code=202)
def ingest_event(
    event: EventEnvelope,
    producer: PulseForgeProducer = Depends(get_event_producer),
):
    try:
        producer.publish(event)
    except Exception:
        logger.exception("Event publication failed: %s", event.event_id)
        raise HTTPException(
            status_code=503,
            detail="Event broker unavailable or delivery unconfirmed",
        )

    return {
        "status": "accepted",
        "event_id": event.event_id,
        "event_name": event.event_name,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/v1/events/batch", status_code=202)
def ingest_batch(
    events: list[EventEnvelope] = Body(min_length=1, max_length=1000),
    producer: PulseForgeProducer = Depends(get_event_producer),
):
    published = 0

    try:
        for event in events:
            producer.publish(event)
            published += 1
    except Exception:
        logger.exception(
            "Batch publication failed after %s confirmed events",
            published,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Batch partially published or delivery unconfirmed",
                "confirmed": published,
                "requested": len(events),
                "retry_warning": "Retry may create duplicate Kafka messages",
            },
        )

    return {
        "status": "accepted",
        "received": len(events),
        "published": published,
    }
