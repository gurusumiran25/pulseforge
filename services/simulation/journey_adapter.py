from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from contracts.event_validation import EventEnvelope
from services.generator.journey_generator import generate_customer_journey
from services.simulation.session_planner import PlannedSession


def generate_planned_journey(session: PlannedSession):
    if not isinstance(session, PlannedSession):
        raise ValueError("session must be a PlannedSession")

    if not session.customer_id or not session.session_id:
        raise ValueError("customer_id and session_id are required")

    start = session.session_start

    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("session_start must be timezone-aware")

    # Stable seed for the same planned session.
    digest = sha256(session.session_id.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big")

    original_events = generate_customer_journey(seed=seed)
    original_start = original_events[0].event_time

    order_id = str(
        uuid5(NAMESPACE_URL, f"pulseforge:order:{session.session_id}")
    )

    converted = []

    for index, original in enumerate(original_events):
        properties = dict(original.properties)

        if original.event_name in (
            "payment_succeeded",
            "payment_failed",
            "order_refunded",
        ):
            properties["order_id"] = order_id

        event_id = str(
            uuid5(
                NAMESPACE_URL,
                f"pulseforge:event:{session.session_id}:{index}",
            )
        )

        event_time = start + (
            original.event_time - original_start
        )

        updated = original.model_copy(
            update={
                "event_id": event_id,
                "user_id": session.customer_id,
                "session_id": session.session_id,
                "event_time": event_time,
                "properties": properties,
            }
        )

        # Revalidate the complete modified event.
        validated = EventEnvelope.model_validate(
            updated.model_dump()
        )
        converted.append(validated)

    return converted
