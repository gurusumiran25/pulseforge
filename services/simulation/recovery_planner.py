from datetime import date, timedelta

from services.simulation.run_health import check_run


def plan_recovery(log_path, start_date, end_date, max_days=7):
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    if end < start:
        raise ValueError("End date cannot precede start date")

    if not 1 <= max_days <= 30:
        raise ValueError("max_days must be between 1 and 30")

    pending = []
    current = start

    while current <= end:
        day = current.isoformat()
        health = check_run(log_path, day)

        if health["status"] != "completed":
            pending.append({
                "date": day,
                "status": health["status"],
            })

            if len(pending) >= max_days:
                break

        current += timedelta(days=1)

    return pending
