from collections import defaultdict
from datetime import datetime, timezone

from contracts.event_validation import EventEnvelope
from services.simulation.customer_behavior import get_customer_behavior
from services.simulation.persona_journey import generate_persona_journey
from services.simulation.session_planner import plan_daily_sessions


def sample_sessions(count=200):
    customers = [f"persona-test-{i:05d}" for i in range(count)]
    return plan_daily_sessions(
        customers,
        datetime(2026, 11, 2, tzinfo=timezone.utc),
        seed=42,
    )


def test_persona_events_are_valid():
    for session in sample_sessions(50):
        for event in generate_persona_journey(session):
            EventEnvelope.model_validate(event.model_dump())


def test_customer_identity_is_preserved():
    for session in sample_sessions(50):
        events = generate_persona_journey(session)
        assert all(e.user_id == session.customer_id for e in events)
        assert all(e.session_id == session.session_id for e in events)


def test_persona_journey_is_deterministic():
    session = sample_sessions(1)[0]
    first = generate_persona_journey(session)
    second = generate_persona_journey(session)

    assert [e.model_dump() for e in first] == [
        e.model_dump() for e in second
    ]


def test_event_ids_are_unique():
    events = [
        event
        for session in sample_sessions(100)
        for event in generate_persona_journey(session)
    ]

    assert len(events) == len({e.event_id for e in events})


def test_successful_payment_matches_checkout():
    for session in sample_sessions(200):
        events = generate_persona_journey(session)
        checkout = next(
            (e for e in events if e.event_name == "checkout_started"),
            None,
        )
        payment = next(
            (e for e in events if e.event_name == "payment_succeeded"),
            None,
        )

        if payment:
            assert checkout is not None
            assert payment.properties["amount"] == checkout.properties["cart_value"]


def test_personas_show_different_purchase_rates():
    sessions = sample_sessions(3000)
    counts = defaultdict(int)
    purchases = defaultdict(int)

    for session in sessions:
        behavior = get_customer_behavior(session.customer_id)
        counts[behavior.segment] += 1

        events = generate_persona_journey(session)
        if any(e.event_name == "payment_succeeded" for e in events):
            purchases[behavior.segment] += 1

    rates = {
        segment: purchases[segment] / counts[segment]
        for segment in counts
    }

    assert rates["high_value"] > rates["frequent_buyer"]
    assert rates["frequent_buyer"] > rates["price_sensitive"]
    assert rates["price_sensitive"] > rates["casual_browser"]
