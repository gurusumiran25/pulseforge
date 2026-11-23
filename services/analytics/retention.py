"""UTC first-seen user retention from validated synthetic event records.

This is observed activity retention, not subscription or revenue retention.
"""
from collections import defaultdict
from datetime import datetime, timezone


def _utc_date(value):
    if isinstance(value, datetime):
        stamp = value
    elif isinstance(value, str):
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise TypeError("event_time must be an ISO timestamp or datetime")
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("event_time must be timezone-aware")
    return stamp.astimezone(timezone.utc).date()


def calculate_retention(events, *, horizons=(1, 7, 14, 30)):
    """Return cohort sizes and exact-day returning-user retention percentages.

    A user is retained on day N if they have at least one event on exactly
    N UTC calendar days after their first observed event. The first observed
    date is not necessarily the user's true acquisition date.
    """
    if not horizons or any(not isinstance(h, int) or isinstance(h, bool) or h <= 0 for h in horizons):
        raise ValueError("horizons must contain positive integers")
    if len(set(horizons)) != len(horizons):
        raise ValueError("horizons must be unique")
    activity = defaultdict(set)
    for event in events:
        user_id = event["user_id"]
        if not user_id:
            raise ValueError("user_id cannot be empty")
        activity[user_id].add(_utc_date(event["event_time"]))
    cohorts = defaultdict(list)
    for user_id, dates in activity.items():
        cohorts[min(dates)].append(dates)
    results = []
    for cohort_date, members in sorted(cohorts.items()):
        row = {"cohort_date_utc": cohort_date.isoformat(), "users": len(members)}
        for horizon in horizons:
            target = cohort_date.toordinal() + horizon
            retained = sum(any(d.toordinal() == target for d in dates) for dates in members)
            row[f"day_{horizon}_users"] = retained
            row[f"day_{horizon}_retention_pct"] = round(retained / len(members) * 100, 2)
        results.append(row)
    return {"definition": "exact-day UTC activity retention from first observed event", "cohorts": results}
