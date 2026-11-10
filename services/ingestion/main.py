from datetime import datetime, timezone

from fastapi import Depends, FastAPI

from contracts.event_validation import EventEnvelope
from services.storage.sqlite_store import SQLiteEventStore


app = FastAPI(
    title="PulseForge Event Ingestion API",
    version="0.2.0",
    description="Validated product analytics event ingestion with SQLite persistence",
)


def get_event_store():
    return SQLiteEventStore()


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "pulseforge-ingestion"}


@app.post("/v1/events", status_code=202)
def ingest_event(
    event: EventEnvelope,
    store: SQLiteEventStore = Depends(get_event_store),
):
    inserted = store.insert_event(event)

    return {
        "status": "stored" if inserted else "duplicate",
        "event_id": event.event_id,
        "event_name": event.event_name,
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
