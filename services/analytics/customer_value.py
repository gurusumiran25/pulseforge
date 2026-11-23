"""Observed customer net payment value, not predictive lifetime value.

Currency-isolated successful order value minus valid refunds. Refunds can
appear before their matching success event in the input sequence.
"""
from collections import defaultdict
from decimal import Decimal, InvalidOperation


def _amount(value, *, allow_zero=False):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Invalid monetary amount") from exc
    if not amount.is_finite() or (amount < 0 if allow_zero else amount <= 0):
        raise ValueError("Monetary amount must be finite and nonnegative" if allow_zero else "Monetary amount must be positive and finite")
    return amount


def calculate_observed_customer_value(events):
    """Compute observed gross/refund/net totals per user and currency.

    Successful orders are deduplicated by order_id; refunds are summed by
    order_id and must not exceed the matching payment. This is historical
    realized value only, not a future-looking CLV prediction.
    """
    orders = {}
    refunds = defaultdict(lambda: Decimal("0"))
    for event in events:
        name = event["event_name"]
        if name not in ("payment_succeeded", "order_refunded"):
            continue
        props = event["properties"]
        order_id = props["order_id"]
        currency = props["currency"]
        if not order_id or not currency:
            raise ValueError("Missing order_id or currency")
        if name == "payment_succeeded":
            user_id = event["user_id"]
            if not user_id:
                raise ValueError("Missing user_id")
            amount = _amount(props["amount"])
            candidate = (user_id, currency, amount)
            if order_id in orders and orders[order_id] != candidate:
                raise ValueError("Conflicting successful payment for order")
            orders[order_id] = candidate
        else:
            refunds[(order_id, currency)] += _amount(props["refund_amount"], allow_zero=False)
    for (order_id, currency), total in refunds.items():
        if order_id not in orders:
            raise ValueError("Refund references unknown successful order")
        if orders[order_id][1] != currency:
            raise ValueError("Refund currency mismatch")
        if total > orders[order_id][2]:
            raise ValueError("Refund exceeds successful payment")
    customers = defaultdict(lambda: {"orders": 0, "gross": Decimal("0"), "refunds": Decimal("0")})
    for order_id, (user_id, currency, amount) in orders.items():
        bucket = customers[(user_id, currency)]
        bucket["orders"] += 1
        bucket["gross"] += amount
        bucket["refunds"] += refunds[(order_id, currency)]
    result = []
    for (user_id, currency), totals in sorted(customers.items()):
        result.append({
            "user_id": user_id,
            "currency": currency,
            "unique_orders": totals["orders"],
            "gross_payment_value": str(totals["gross"]),
            "refunded_value": str(totals["refunds"]),
            "observed_net_value": str(totals["gross"] - totals["refunds"]),
        })
    return {"definition": "historical observed net payment value; not predictive CLV", "customers": result}
