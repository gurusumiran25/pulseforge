"""M59 observed customer value regression tests."""
import pytest

from services.analytics.customer_value import calculate_observed_customer_value


def payment(user, order, amount, currency="USD"):
    return {"event_name": "payment_succeeded", "user_id": user,
            "properties": {"order_id": order, "currency": currency, "amount": amount}}


def refund(order, amount, currency="USD"):
    return {"event_name": "order_refunded",
            "properties": {"order_id": order, "currency": currency, "refund_amount": amount}}


def test_value_deduplicates_orders_and_handles_partial_refunds():
    result = calculate_observed_customer_value([
        refund("o1", "3.25"), payment("u", "o1", "10.00"),
        payment("u", "o1", "10.00"), payment("u", "o2", "5.00"),
    ])["customers"][0]
    assert result == {"user_id": "u", "currency": "USD", "unique_orders": 2,
                      "gross_payment_value": "15.00", "refunded_value": "3.25",
                      "observed_net_value": "11.75"}


def test_currency_isolation():
    rows = calculate_observed_customer_value([
        payment("u", "o1", "10", "USD"), payment("u", "o2", "20", "INR"),
    ])["customers"]
    assert {r["currency"]: r["observed_net_value"] for r in rows} == {"INR": "20", "USD": "10"}


def test_full_refund_is_zero_value():
    row = calculate_observed_customer_value([payment("u", "o1", "7"), refund("o1", "7")])["customers"][0]
    assert row["observed_net_value"] == "0"


@pytest.mark.parametrize("events", [
    [refund("unknown", "2")],
    [payment("u", "o1", "2"), refund("o1", "3")],
    [payment("u", "o1", "2"), refund("o1", "1", "INR")],
    [payment("u", "o1", "2"), payment("v", "o1", "2")],
    [payment("u", "o1", "NaN")],
    [payment("u", "o1", "-2")],
])
def test_invalid_transactions_fail_closed(events):
    with pytest.raises(ValueError):
        calculate_observed_customer_value(events)


def test_empty_and_non_payment_events():
    assert calculate_observed_customer_value([{"event_name": "page_view"}])["customers"] == []
