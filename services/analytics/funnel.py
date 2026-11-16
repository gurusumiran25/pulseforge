from services.storage.sqlite_store import SQLiteEventStore


FUNNEL_STAGES = (
    "page_view",
    "search_performed",
    "product_viewed",
    "add_to_cart",
    "checkout_started",
    "payment_succeeded",
)


def calculate_funnel(db_path="data/storage/pulseforge.db"):
    """Calculate ordered, session-level funnel conversion."""
    store = SQLiteEventStore(db_path)

    with store.connect() as connection:
        rows = connection.execute(
            """
            SELECT session_id, event_name, event_time, event_id
            FROM events
            ORDER BY session_id, event_time, event_id
            """
        ).fetchall()

    sessions = {}

    for row in rows:
        sessions.setdefault(row["session_id"], []).append(
            row["event_name"]
        )

    counts = {stage: 0 for stage in FUNNEL_STAGES}

    for event_names in sessions.values():
        next_stage = 0

        for event_name in event_names:
            if (
                next_stage < len(FUNNEL_STAGES)
                and event_name == FUNNEL_STAGES[next_stage]
            ):
                counts[event_name] += 1
                next_stage += 1

    total_sessions = len(sessions)
    previous_count = None
    result = []

    for stage in FUNNEL_STAGES:
        count = counts[stage]

        overall_rate = (
            round(count / total_sessions * 100, 2)
            if total_sessions else 0.0
        )

        step_rate = (
            round(count / previous_count * 100, 2)
            if previous_count else 0.0
        ) if previous_count is not None else None

        result.append({
            "stage": stage,
            "sessions": count,
            "overall_conversion_pct": overall_rate,
            "step_conversion_pct": step_rate,
            "drop_off_sessions": (
                previous_count - count
                if previous_count is not None else None
            ),
        })

        previous_count = count

    return {
        "total_sessions": total_sessions,
        "funnel": result,
    }
