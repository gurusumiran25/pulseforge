import random
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from contracts.event_validation import EventEnvelope


PRODUCTS = [
    {"id": "P101", "category": "Electronics", "price": 2499.0},
    {"id": "P102", "category": "Fashion", "price": 899.0},
    {"id": "P103", "category": "Home", "price": 1599.0},
    {"id": "P104", "category": "Books", "price": 499.0},
]


def generate_customer_journey(seed=None):
    rng = random.Random(seed)
    user_id = f"user_{uuid4().hex[:12]}"
    session_id = f"session_{uuid4().hex[:12]}"
    product = rng.choice(PRODUCTS)
    start_time = datetime.now(timezone.utc)

    events = []

    def add_event(name, properties):
        event_time = start_time + timedelta(seconds=len(events) * 30)

        event = EventEnvelope(
            event_id=str(uuid4()),
            event_name=name,
            schema_version=1,
            event_time=event_time,
            user_id=user_id,
            session_id=session_id,
            source="synthetic_generator",
            platform="web",
            properties=properties,
        )
        events.append(event)

    add_event("page_view", {"page_path": "/"})

    add_event(
        "search_performed",
        {"search_category": product["category"], "result_count": 12},
    )

    add_event(
        "product_viewed",
        {
            "product_id": product["id"],
            "category": product["category"],
            "price": product["price"],
            "currency": "INR",
        },
    )

    if rng.random() < 0.30:
        return events

    add_event(
        "add_to_cart",
        {
            "product_id": product["id"],
            "quantity": 1,
            "unit_price": product["price"],
            "currency": "INR",
        },
    )

    if rng.random() < 0.25:
        return events

    add_event(
        "checkout_started",
        {
            "cart_value": product["price"],
            "item_count": 1,
            "currency": "INR",
        },
    )

    order_id = f"order_{uuid4().hex[:12]}"

    if rng.random() < 0.80:
        add_event(
            "payment_succeeded",
            {
                "order_id": order_id,
                "amount": product["price"],
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


if __name__ == "__main__":
    journey = generate_customer_journey(seed=42)

    for event in journey:
        print(event.model_dump_json())
