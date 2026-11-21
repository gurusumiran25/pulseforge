"""Pure, testable M21 dashboard calculations from the synthetic Bronze seed.

Stage flags are observations, NOT an ordered conversion funnel.
Dates are UTC and session cohort dates use the earliest event.
"""
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


SEED_PATH = Path(__file__).resolve().parents[2] / "warehouse/dbt/seeds/bronze_events.csv"
STAGES = ("product_viewed", "add_to_cart", "checkout_started", "payment_succeeded")


def load_events(path=SEED_PATH):
    with Path(path).open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    required = {"event_id", "event_name", "session_id", "user_id", "event_time"}
    if any(not required.issubset(row) for row in rows):
        raise ValueError("Missing required Bronze event fields")
    if any(not all(row.get(field) for field in required) for row in rows):
        raise ValueError("Blank required Bronze event field")
    if len({row["event_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate event_id in dashboard source")
    for row in rows:
        row["event_time"] = datetime.fromisoformat(row["event_time"].replace("Z", "+00:00"))
        if row["event_time"].tzinfo is None:
            # The synthetic CSV stores UTC without an explicit offset.
            row["event_time"] = row["event_time"].replace(tzinfo=timezone.utc)
        row["event_time"] = row["event_time"].astimezone(timezone.utc)
    return rows


def summarize(events):
    sessions = defaultdict(list)
    for event in events:
        sessions[event["session_id"]].append(event)

    session_rows = []
    for session_id, rows in sessions.items():
        names = {row["event_name"] for row in rows}
        first = min(row["event_time"] for row in rows)
        session_rows.append({
            "session_id": session_id,
            "cohort_date_utc": first.date().isoformat(),
            "event_count": len(rows),
            **{stage: int(stage in names) for stage in STAGES},
        })
    session_rows.sort(key=lambda row: (row["cohort_date_utc"], row["session_id"]))

    daily = defaultdict(lambda: {"sessions": 0, **{stage: 0 for stage in STAGES}})
    for row in session_rows:
        bucket = daily[row["cohort_date_utc"]]
        bucket["sessions"] += 1
        for stage in STAGES:
            bucket[stage] += row[stage]

    activity = defaultdict(lambda: {"events": 0, "users": set()})
    for event in events:
        date = event["event_time"].date().isoformat()
        activity[date]["events"] += 1
        activity[date]["users"].add(event["user_id"])

    return {
        "events": len(events),
        "sessions": len(sessions),
        "users": len({event["user_id"] for event in events}),
        "paid_sessions": sum(row["payment_succeeded"] for row in session_rows),
        "session_rows": session_rows,
        "daily_funnel": [{"date": day, **daily[day]} for day in sorted(daily)],
        "daily_activity": [
            {"date": day, "events": activity[day]["events"], "active_users": len(activity[day]["users"])}
            for day in sorted(activity)
        ],
    }
