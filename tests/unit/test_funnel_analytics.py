from datetime import datetime, timedelta, timezone

from contracts.event_validation import EventEnvelope
from services.analytics.funnel import calculate_funnel
from services.storage.sqlite_store import SQLiteEventStore


def make_event(event_id, session_id, event_name, second):
    properties = {
        "page_view": {"page_path": "/"},
        "search_performed": {
            "search_category": "Books",
            "result_count": 2,
        },
        "product_viewed": {
            "product_id": "P1",
            "category": "Books",
            "price": 100,
            "currency": "INR",
        },
        "add_to_cart": {
            "product_id": "P1",
            "quantity": 1,
            "unit_price": 100,
            "currency": "INR",
        },
        "checkout_started": {
            "cart_value": 100,
            "item_count": 1,
            "currency": "INR",
        },
        "payment_succeeded": {
            "order_id": "O1",
            "amount": 100,
            "currency": "INR",
            "payment_method_category": "UPI",
        },
    }

    return EventEnvelope(
        event_id=event_id,
        event_name=event_name,
        schema_version=1,
        event_time=datetime(2026, 1, 1, tzinfo=timezone.utc)
        + timedelta(seconds=second),
        user_id=session_id,
        session_id=session_id,
        source="pytest",
        platform="web",
        properties=properties[event_name],
    )


def test_empty_funnel(tmp_path):
    result = calculate_funnel(tmp_path / "empty.db")
    assert result["total_sessions"] == 0
    assert all(x["sessions"] == 0 for x in result["funnel"])


def test_ordered_funnel_and_dropoff(tmp_path):
    db = tmp_path / "funnel.db"
    store = SQLiteEventStore(db)

    stages = [
        "page_view",
        "search_performed",
        "product_viewed",
        "add_to_cart",
        "checkout_started",
        "payment_succeeded",
    ]

    events = [
        make_event(f"a-{i}", "session-a", stage, i)
        for i, stage in enumerate(stages)
    ]

    events += [
        make_event("b-0", "session-b", "page_view", 0),
        make_event("b-1", "session-b", "search_performed", 1),
        make_event("b-2", "session-b", "product_viewed", 2),
    ]

    store.insert_events_bulk(events)
    result = calculate_funnel(db)

    assert result["total_sessions"] == 2
    assert [x["sessions"] for x in result["funnel"]] == [
        2, 2, 2, 1, 1, 1
    ]
    assert result["funnel"][3]["drop_off_sessions"] == 1
    assert result["funnel"][3]["step_conversion_pct"] == 50.0


def test_out_of_order_events_do_not_complete_funnel(tmp_path):
    db = tmp_path / "out_of_order.db"
    store = SQLiteEventStore(db)

    events = [
        make_event("x-0", "session-x", "payment_succeeded", 0),
        make_event("x-1", "session-x", "page_view", 1),
        make_event("x-2", "session-x", "search_performed", 2),
    ]

    store.insert_events_bulk(events)
    result = calculate_funnel(db)

    assert [x["sessions"] for x in result["funnel"]] == [
        1, 1, 0, 0, 0, 0
    ]
