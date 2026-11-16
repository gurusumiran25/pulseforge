import random
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from services.simulation.customer_registry import CustomerRegistry


@dataclass
class CustomerSelection:
    customer_ids: list[str]
    new_customer_ids: list[str]
    returning_customer_ids: list[str]


class CustomerSelector:
    def __init__(self, registry: CustomerRegistry, seed=None):
        self.registry = registry
        self.random = random.Random(seed)

    def select_daily_customers(
        self,
        total_customers,
        returning_ratio=0.30,
        activity_at=None,
    ):
        if isinstance(total_customers, bool) or not isinstance(
            total_customers, int
        ) or not 1 <= total_customers <= 6000:
            raise ValueError("total_customers must be between 1 and 6000")

        if not 0 <= returning_ratio <= 1:
            raise ValueError("returning_ratio must be between 0 and 1")

        if activity_at is None:
            activity_at = datetime.now(timezone.utc)

        if (
            activity_at.tzinfo is None
            or activity_at.utcoffset() is None
        ):
            raise ValueError("activity_at must be timezone-aware")

        activity_at = activity_at.astimezone(timezone.utc)
        timestamp = activity_at.isoformat()

        # Only customers who existed before this activity time
        # can be considered returning customers.
        with self.registry.connect() as connection:
            rows = connection.execute(
                """
                SELECT customer_id
                FROM customers
                WHERE first_seen < ?
                ORDER BY customer_id
                """,
                (timestamp,),
            ).fetchall()

        eligible_ids = [row["customer_id"] for row in rows]

        requested_returning = round(
            total_customers * returning_ratio
        )
        returning_count = min(
            requested_returning,
            len(eligible_ids),
        )

        returning_ids = self.random.sample(
            eligible_ids,
            returning_count,
        )

        new_count = total_customers - returning_count
        new_ids = [
            f"customer-{uuid4().hex}"
            for _ in range(new_count)
        ]

        for customer_id in returning_ids + new_ids:
            self.registry.register_customer(
                customer_id,
                activity_at,
            )

        customer_ids = returning_ids + new_ids
        self.random.shuffle(customer_ids)

        return CustomerSelection(
            customer_ids=customer_ids,
            new_customer_ids=new_ids,
            returning_customer_ids=returning_ids,
        )
