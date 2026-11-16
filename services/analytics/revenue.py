import json
from collections import defaultdict
from decimal import Decimal

from services.storage.sqlite_store import SQLiteEventStore


def calculate_revenue(db_path="data/storage/pulseforge.db"):
    store = SQLiteEventStore(db_path)

    with store.connect() as connection:
        rows = connection.execute(
            """
            SELECT event_name, payload
            FROM events
            WHERE event_name IN (
                'payment_succeeded',
                'payment_failed',
                'order_refunded'
            )
            ORDER BY event_time, event_id
            """
        ).fetchall()

    orders = {}
    refunds = defaultdict(lambda: Decimal("0"))

    succeeded = 0
    failed = 0
    refund_events = 0
    duplicate_success_events = 0

    for row in rows:
        event = json.loads(row["payload"])
        props = event["properties"]
        name = row["event_name"]

        if name == "payment_failed":
            failed += 1
            continue

        order_id = props["order_id"]

        if name == "payment_succeeded":
            succeeded += 1
            currency = props["currency"]
            amount = Decimal(str(props["amount"]))

            if order_id in orders:
                previous = orders[order_id]

                if (
                    previous["currency"] != currency
                    or previous["amount"] != amount
                ):
                    raise ValueError(
                        f"Conflicting successful payments for order {order_id}"
                    )

                duplicate_success_events += 1
                continue

            orders[order_id] = {
                "currency": currency,
                "amount": amount,
            }

        elif name == "order_refunded":
            refund_events += 1
            currency = props["currency"]
            amount = Decimal(str(props["refund_amount"]))
            refunds[(order_id, currency)] += amount

    for (order_id, currency), refund_total in refunds.items():
        original = orders.get(order_id)

        if original is None:
            raise ValueError(
                f"Refund references unknown order {order_id}"
            )

        if original["currency"] != currency:
            raise ValueError(
                f"Refund currency mismatch for order {order_id}"
            )

        if refund_total > original["amount"]:
            raise ValueError(
                f"Refund exceeds payment for order {order_id}"
            )

    currencies = defaultdict(
        lambda: {
            "gross": Decimal("0"),
            "refunds": Decimal("0"),
            "orders": 0,
        }
    )

    for order_id, order in orders.items():
        currency = order["currency"]

        currencies[currency]["gross"] += order["amount"]
        currencies[currency]["orders"] += 1
        currencies[currency]["refunds"] += refunds[
            (order_id, currency)
        ]

    by_currency = {}

    for currency, values in sorted(currencies.items()):
        gross = values["gross"]
        refund_total = values["refunds"]
        count = values["orders"]

        by_currency[currency] = {
            "gross_payment_value": float(gross),
            "refund_value": float(refund_total),
            "net_payment_value": float(gross - refund_total),
            "unique_successful_orders": count,
            "average_order_value": (
                float(gross / count) if count else 0.0
            ),
        }

    attempts = succeeded + failed

    return {
        "successful_payment_events": succeeded,
        "failed_payment_events": failed,
        "refund_events": refund_events,
        "duplicate_success_events": duplicate_success_events,
        "payment_outcome_events": attempts,
        "payment_success_pct": (
            round(succeeded / attempts * 100, 2)
            if attempts else 0.0
        ),
        "by_currency": by_currency,
    }
