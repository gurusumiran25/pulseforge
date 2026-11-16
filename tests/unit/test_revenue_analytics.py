from datetime import datetime, timezone

import pytest

from contracts.event_validation import EventEnvelope
from services.analytics.revenue import calculate_revenue
from services.storage.sqlite_store import SQLiteEventStore


def make_event(event_id, name, order_id, currency="INR", amount=100):
    properties = {
        "payment_succeeded": {
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "payment_method_category": "UPI",
        },
        "payment_failed": {
            "order_id": order_id,
            "failure_code_category": "DECLINED",
        },
        "order_refunded": {
            "order_id": order_id,
            "refund_amount": amount,
            "currency": currency,
            "reason_category": "CUSTOMER_REQUEST",
        },
    }

    return EventEnvelope(
        event_id=event_id,
        event_name=name,
        schema_version=1,
        event_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        user_id="user-test",
        session_id="session-test",
        source="pytest",
        platform="web",
        properties=properties[name],
    )


def test_empty_revenue(tmp_path):
    result = calculate_revenue(tmp_path / "empty.db")

    assert result["successful_payment_events"] == 0
    assert result["failed_payment_events"] == 0
    assert result["payment_success_pct"] == 0
    assert result["by_currency"] == {}


def test_success_and_failure_rate(tmp_path):
    db = tmp_path / "payments.db"
    store = SQLiteEventStore(db)

    store.insert_events_bulk([
        make_event("e1", "payment_succeeded", "o1", amount=200),
        make_event("e2", "payment_succeeded", "o2", amount=100),
        make_event("e3", "payment_failed", "o3"),
    ])

    result = calculate_revenue(db)

    assert result["successful_payment_events"] == 2
    assert result["failed_payment_events"] == 1
    assert result["payment_success_pct"] == 66.67
    assert result["by_currency"]["INR"]["gross_payment_value"] == 300
    assert result["by_currency"]["INR"]["average_order_value"] == 150


def test_refund_reduces_net_value(tmp_path):
    db = tmp_path / "refund.db"
    store = SQLiteEventStore(db)

    store.insert_events_bulk([
        make_event("e1", "payment_succeeded", "o1", amount=500),
        make_event("e2", "order_refunded", "o1", amount=200),
    ])

    result = calculate_revenue(db)
    inr = result["by_currency"]["INR"]

    assert result["refund_events"] == 1
    assert inr["gross_payment_value"] == 500
    assert inr["refund_value"] == 200
    assert inr["net_payment_value"] == 300


def test_currencies_are_separate(tmp_path):
    db = tmp_path / "currencies.db"
    store = SQLiteEventStore(db)

    store.insert_events_bulk([
        make_event("e1", "payment_succeeded", "o1", "INR", 1000),
        make_event("e2", "payment_succeeded", "o2", "USD", 20),
    ])

    result = calculate_revenue(db)

    assert result["by_currency"]["INR"]["gross_payment_value"] == 1000
    assert result["by_currency"]["USD"]["gross_payment_value"] == 20
    assert set(result["by_currency"]) == {"INR", "USD"}


def test_duplicate_event_id_not_double_counted(tmp_path):
    db = tmp_path / "duplicate.db"
    store = SQLiteEventStore(db)

    event = make_event("e1", "payment_succeeded", "o1", amount=250)

    assert store.insert_event(event) is True
    assert store.insert_event(event) is False

    result = calculate_revenue(db)

    assert result["successful_payment_events"] == 1
    assert result["by_currency"]["INR"]["gross_payment_value"] == 250


def test_same_order_different_event_ids_not_double_counted(tmp_path):
    db = tmp_path / "same_order.db"
    store = SQLiteEventStore(db)

    store.insert_events_bulk([
        make_event("event-1", "payment_succeeded", "order-100", amount=500),
        make_event("event-2", "payment_succeeded", "order-100", amount=500),
    ])

    result = calculate_revenue(db)
    inr = result["by_currency"]["INR"]

    assert inr["unique_successful_orders"] == 1
    assert inr["gross_payment_value"] == 500
    assert inr["average_order_value"] == 500


def test_conflicting_order_amount_rejected(tmp_path):
    db = tmp_path / "conflict.db"
    store = SQLiteEventStore(db)

    store.insert_events_bulk([
        make_event("e1", "payment_succeeded", "o1", amount=500),
        make_event("e2", "payment_succeeded", "o1", amount=700),
    ])

    with pytest.raises(ValueError, match="Conflicting"):
        calculate_revenue(db)


def test_multiple_partial_refunds(tmp_path):
    db = tmp_path / "partial_refunds.db"
    store = SQLiteEventStore(db)

    store.insert_events_bulk([
        make_event("e1", "payment_succeeded", "o1", amount=500),
        make_event("e2", "order_refunded", "o1", amount=100),
        make_event("e3", "order_refunded", "o1", amount=150),
    ])

    result = calculate_revenue(db)
    inr = result["by_currency"]["INR"]

    assert inr["gross_payment_value"] == 500
    assert inr["refund_value"] == 250
    assert inr["net_payment_value"] == 250


def test_refund_exceeding_payment_rejected(tmp_path):
    db = tmp_path / "excess_refund.db"
    store = SQLiteEventStore(db)

    store.insert_events_bulk([
        make_event("e1", "payment_succeeded", "o1", amount=500),
        make_event("e2", "order_refunded", "o1", amount=300),
        make_event("e3", "order_refunded", "o1", amount=300),
    ])

    with pytest.raises(ValueError, match="exceeds payment"):
        calculate_revenue(db)


def test_refund_without_successful_order_rejected(tmp_path):
    db = tmp_path / "orphan_refund.db"
    store = SQLiteEventStore(db)

    store.insert_event(
        make_event("e1", "order_refunded", "unknown", amount=100)
    )

    with pytest.raises(ValueError, match="unknown order"):
        calculate_revenue(db)


def test_conflicting_order_currency_rejected(tmp_path):
    db = tmp_path / "currency_conflict.db"
    store = SQLiteEventStore(db)

    store.insert_events_bulk([
        make_event("e1", "payment_succeeded", "o1", "INR", 500),
        make_event("e2", "payment_succeeded", "o1", "USD", 500),
    ])

    with pytest.raises(ValueError, match="Conflicting"):
        calculate_revenue(db)


def test_refund_currency_mismatch_rejected(tmp_path):
    db = tmp_path / "refund_currency.db"
    store = SQLiteEventStore(db)

    store.insert_events_bulk([
        make_event("e1", "payment_succeeded", "o1", "INR", 500),
        make_event("e2", "order_refunded", "o1", "USD", 100),
    ])

    with pytest.raises(ValueError, match="currency mismatch"):
        calculate_revenue(db)
