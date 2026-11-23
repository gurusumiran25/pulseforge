"""Currency-safe RFM customer segmentation for synthetic payment events.

RFM uses successful gross payments, not net revenue or CLV. Never sum currencies.
"""
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation


def _timestamp(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise TypeError("event_time must be an ISO timestamp or datetime")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("event_time must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def calculate_rfm(events, *, as_of_date):
    """Group unique successful orders per user and currency.

    Recency is elapsed UTC calendar days since the most recent successful payment.
    Frequency counts unique successful order IDs. Monetary sums gross payment
    amounts in a single currency. Segment thresholds are illustrative heuristics.
    """
    if not isinstance(as_of_date, date) or isinstance(as_of_date, datetime):
        raise TypeError("as_of_date must be a date")
    orders = {}
    for event in events:
        if event["event_name"] != "payment_succeeded":
            continue
        user_id = event["user_id"]
        props = event["properties"]
        order_id = props["order_id"]
        currency = props["currency"]
        if not user_id or not order_id or not currency:
            raise ValueError("Payment requires user_id, order_id and currency")
        try:
            amount = Decimal(str(props["amount"]))
        except (InvalidOperation, TypeError) as exc:
            raise ValueError("Invalid payment amount") from exc
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Payment amount must be positive and finite")
        paid_at = _timestamp(event["event_time"])
        if paid_at.date() > as_of_date:
            raise ValueError("Payment occurs after snapshot date")
        key = order_id
        candidate = (user_id, currency, amount)
        if key in orders:
            if orders[key][:3] != candidate:
                raise ValueError("Conflicting successful payment for order")
            continue
        orders[key] = (*candidate, paid_at)
    aggregates = defaultdict(lambda: {"frequency": 0, "monetary": Decimal("0"), "last_payment": None})
    for user_id, currency, amount, paid_at in orders.values():
        bucket = aggregates[(user_id, currency)]
        bucket["frequency"] += 1
        bucket["monetary"] += amount
        if bucket["last_payment"] is None or paid_at > bucket["last_payment"]:
            bucket["last_payment"] = paid_at
    customers = []
    for (user_id, currency), bucket in sorted(aggregates.items()):
        recency = (as_of_date - bucket["last_payment"].date()).days
        frequency = bucket["frequency"]
        if recency <= 7 and frequency >= 3:
            segment = "champions"
        elif recency <= 30 and frequency >= 2:
            segment = "loyal"
        elif recency <= 30:
            segment = "recent"
        else:
            segment = "at_risk"
        customers.append({
            "user_id": user_id,
            "currency": currency,
            "recency_days": recency,
            "frequency_orders": frequency,
            "monetary_gross": str(bucket["monetary"]),
            "segment": segment,
        })
    return {"as_of_date_utc": as_of_date.isoformat(), "basis": "unique gross successful orders by currency", "customers": customers}
