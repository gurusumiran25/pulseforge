from datetime import timedelta

from contracts.event_validation import EventEnvelope
from services.generator.journey_generator import generate_customer_journey


def test_generator_returns_valid_events():
    events = generate_customer_journey(seed=42)

    assert len(events) >= 3
    assert all(isinstance(event, EventEnvelope) for event in events)


def test_events_share_user_and_session():
    events = generate_customer_journey(seed=42)

    assert len({event.user_id for event in events}) == 1
    assert len({event.session_id for event in events}) == 1


def test_events_have_unique_ids():
    events = generate_customer_journey(seed=42)

    assert len({event.event_id for event in events}) == len(events)


def test_events_are_chronological():
    events = generate_customer_journey(seed=42)

    for previous, current in zip(events, events[1:]):
        assert current.event_time - previous.event_time == timedelta(seconds=30)


def test_journey_starts_with_expected_events():
    events = generate_customer_journey(seed=42)

    assert [event.event_name for event in events[:3]] == [
        "page_view",
        "search_performed",
        "product_viewed",
    ]


def test_multiple_seeds_produce_valid_journeys():
    for seed in range(100):
        events = generate_customer_journey(seed=seed)

        assert 3 <= len(events) <= 6

        names = [event.event_name for event in events]

        if "payment_succeeded" in names or "payment_failed" in names:
            assert "checkout_started" in names
            assert "add_to_cart" in names

        assert not (
            "payment_succeeded" in names and "payment_failed" in names
        )
