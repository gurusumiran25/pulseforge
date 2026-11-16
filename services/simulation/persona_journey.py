import random
from datetime import timedelta
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from contracts.event_validation import EventEnvelope
from services.generator.journey_generator import PRODUCTS
from services.simulation.customer_behavior import get_customer_behavior
from services.simulation.session_planner import PlannedSession


def generate_persona_journey(session: PlannedSession):
    if not isinstance(session, PlannedSession):
        raise ValueError("Expected a PlannedSession")

    if not session.customer_id or not session.session_id:
        raise ValueError("Customer and session IDs are required")

    start = session.session_start

    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError("Session timestamp must be timezone-aware")

    behavior = get_customer_behavior(session.customer_id)

    if session.segment != behavior.segment:
        raise ValueError("Session segment does not match customer persona")

    digest = sha256(session.session_id.encode("utf-8")).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))

    product = rng.choice(PRODUCTS)
    price = round(
        product["price"] * behavior.average_basket_multiplier, 2
    )

    # Decide purchase outcome once per session.
    will_purchase = rng.random() < behavior.purchase_probability

    events = []

    def add_event(name, properties):
        index = len(events)

        event = EventEnvelope(
            event_id=str(
                uuid5(
                    NAMESPACE_URL,
                    f"pulseforge:persona:event:{session.session_id}:{index}",
                )
            ),
            event_name=name,
            schema_version=1,
            event_time=start + timedelta(seconds=index * 30),
            user_id=session.customer_id,
            session_id=session.session_id,
            source="synthetic_persona_generator",
            platform="web",
            properties=properties,
        )
        events.append(event)

    add_event("page_view", {"page_path": "/"})

    # Non-purchasing sessions can exit at different funnel stages.
    if not will_purchase and rng.random() < 0.15:
        return events

    add_event(
        "search_performed",
        {
            "search_category": product["category"],
            "result_count": 12,
        },
    )

    add_event(
        "product_viewed",
        {
            "product_id": product["id"],
            "category": product["category"],
            "price": price,
            "currency": "INR",
        },
    )

    if not will_purchase and rng.random() < 0.50:
        return events

    add_event(
        "add_to_cart",
        {
            "product_id": product["id"],
            "quantity": 1,
            "unit_price": price,
            "currency": "INR",
        },
    )

    if not will_purchase and rng.random() < 0.65:
        return events

    add_event(
        "checkout_started",
        {
            "cart_value": price,
            "item_count": 1,
            "currency": "INR",
        },
    )

    order_id = str(
        uuid5(
            NAMESPACE_URL,
            f"pulseforge:persona:order:{session.session_id}",
        )
    )

    if will_purchase:
        add_event(
            "payment_succeeded",
            {
                "order_id": order_id,
                "amount": price,
                "currency": "INR",
                "payment_method_category": "UPI",
            },
        )
    else:
        add_event(
            "payment_failed",
            {
                "order_id": order_id,
                "failure_code_category": "DECLINED",
            },
        )

    return events
