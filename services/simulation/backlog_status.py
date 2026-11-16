from datetime import date, timedelta

from services.simulation.run_health import check_run


def check_backlog_status(log_path, start_date, target_date):
    start = date.fromisoformat(start_date)
    target = date.fromisoformat(target_date)

    if target < start:
        raise ValueError("Target date cannot precede start date")

    missing = []
    current = start

    while current <= target:
        result = check_run(log_path, current.isoformat())

        if result["status"] != "completed":
            missing.append({
                "date": current.isoformat(),
                "status": result["status"],
            })

        current += timedelta(days=1)

    return {
        "target_date": target.isoformat(),
        "fully_caught_up": len(missing) == 0,
        "pending_count": len(missing),
        "oldest_pending": missing[0]["date"] if missing else None,
        "target_completed": (
            check_run(log_path, target.isoformat())["status"]
            == "completed"
        ),
    }
