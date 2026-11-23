"""M58 RFM segmentation regression coverage."""
from datetime import date

import pytest

from services.analytics.rfm import calculate_rfm


SNAPSHOT = date(2026, 11, 23)


def payment(user, order, amount, *, currency="USD", day="2026-11-20"):
    return {
        "event_name": "payment_succeeded",
        "user_id": user,
        "event_time": f"{day}T12:00:00+00:00",
        "properties": {"order_id": order, "amount": amount, "currency": currency},
    }


def test_rfm_counts_unique_orders_and_segments():
    events = [payment("u", "o1", "10.25"), payment("u", "o1", "10.25"),
              payment("u", "o2", "5.75"), payment("u", "o3", "4")]
    customer = calculate_rfm(events, as_of_date=SNAPSHOT)["customers"][0]
    assert customer == {
        "user_id": "u", "currency": "USD", "recency_days": 3,
        "frequency_orders": 3, "monetary_gross": "20.00", "segment": "champions",
    }


def test_currencies_never_combined():
    rows = calculate_rfm([payment("u", "a", "5", currency="USD"),
                          payment("u", "b", "10", currency="INR")], as_of_date=SNAPSHOT)["customers"]
    assert len(rows) == 2
    assert {r["currency"]: r["monetary_gross"] for r in rows} == {"INR": "10", "USD": "5"}


def test_older_customer_is_at_risk():
    row = calculate_rfm([payment("u", "a", "5", day="2026-10-01")], as_of_date=SNAPSHOT)["customers"][0]
    assert row["segment"] == "at_risk"


def test_non_payment_events_ignored():
    assert calculate_rfm([{"event_name": "page_view"}], as_of_date=SNAPSHOT)["customers"] == []


@pytest.mark.parametrize("amount", ["0", "-1", "NaN", "Infinity", "not-money"])
def test_invalid_amounts_rejected(amount):
    with pytest.raises(ValueError):
        calculate_rfm([payment("u", "a", amount)], as_of_date=SNAPSHOT)


def test_conflicting_duplicate_order_rejected():
    with pytest.raises(ValueError, match="Conflicting"):
        calculate_rfm([payment("u", "a", "5"), payment("u", "a", "7")], as_of_date=SNAPSHOT)


def test_future_payment_rejected():
    with pytest.raises(ValueError, match="after snapshot"):
        calculate_rfm([payment("u", "a", "5", day="2026-11-24")], as_of_date=SNAPSHOT)


def test_snapshot_must_be_date():
    with pytest.raises(TypeError):
        calculate_rfm([], as_of_date="2026-11-23")
