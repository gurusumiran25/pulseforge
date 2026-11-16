from datetime import date, timedelta

from services.simulation.run_health import check_run


class ChronologyViolation(RuntimeError):
    pass


def validate_chronology(log_path, start_date, target_date):
    start = date.fromisoformat(start_date)
    target = date.fromisoformat(target_date)

    if target < start:
        raise ValueError("Target date precedes start date")

    current = start

    while current < target:
        result = check_run(log_path, current.isoformat())

        if result["status"] != "completed":
            raise ChronologyViolation(
                f"Cannot process {target.isoformat()}: "
                f"{current.isoformat()} is {result['status']}"
            )

        current += timedelta(days=1)

    return True
