import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from services.simulation.customer_behavior import get_customer_behavior


@dataclass(frozen=True)
class PlannedSession:
    customer_id: str
    session_id: str
    session_start: datetime
    segment: str


def plan_daily_sessions(customer_ids, activity_date, seed=42):
    if not isinstance(activity_date, datetime):
        raise ValueError("activity_date must be a datetime")

    if (
        activity_date.tzinfo is None
        or activity_date.utcoffset() is None
    ):
        raise ValueError("activity_date must be timezone-aware")

    if len(customer_ids) != len(set(customer_ids)):
        raise ValueError("customer_ids must be unique")

    day = activity_date.astimezone(timezone.utc).date()
    midnight = datetime(
        day.year, day.month, day.day, tzinfo=timezone.utc
    )

    sessions = []

    for customer_id in sorted(customer_ids):
        behavior = get_customer_behavior(customer_id)

        # Stable per-customer, per-day randomness.
        key = f"{seed}:{day.isoformat()}:{customer_id}"
        rng_seed = uuid5(NAMESPACE_URL, key).int
        rng = random.Random(rng_seed)

        if behavior.segment == "casual_browser":
            session_count = 1
        elif behavior.segment == "price_sensitive":
            session_count = rng.randint(1, 2)
        elif behavior.segment == "frequent_buyer":
            session_count = rng.randint(1, 3)
        else:
            session_count = rng.randint(1, 3)

        minutes = sorted(
            rng.sample(range(24 * 60), session_count)
        )

        for index, minute in enumerate(minutes, start=1):
            session_key = (
                f"pulseforge:{day}:{customer_id}:{index}"
            )
            session_id = str(uuid5(NAMESPACE_URL, session_key))

            sessions.append(
                PlannedSession(
                    customer_id=customer_id,
                    session_id=session_id,
                    session_start=midnight + timedelta(minutes=minute),
                    segment=behavior.segment,
                )
            )

    return sorted(
        sessions,
        key=lambda session: (
            session.session_start,
            session.session_id,
        ),
    )
