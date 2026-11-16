import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

from services.simulation.chronology_guard import validate_chronology
from services.simulation.recovery_planner import plan_recovery


def recover_in_order(
    start_date,
    end_date,
    log_path,
    simulation_db,
    event_db,
    customers=500,
    seed=42,
    max_days=7,
    execute=False,
    today=None,
):
    if today is None:
        today = datetime.now(
            timezone(timedelta(hours=5, minutes=30))
        ).date()

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    if end < start:
        raise ValueError("End date cannot precede start date")

    if not 1 <= max_days <= 7:
        raise ValueError("max_days must be between 1 and 7")

    if start > today:
        return []

    end = min(end, today)

    pending = plan_recovery(
        log_path,
        start.isoformat(),
        end.isoformat(),
        max_days=max_days,
    )

    if not execute:
        return pending

    for item in pending:
        day = item["date"]

        validate_chronology(
            log_path,
            start.isoformat(),
            day,
        )

        command = [
            sys.executable,
            "-m",
            "services.simulation.daily_cli",
            "--recovery-worker",
            "--date", day,
            "--customers", str(customers),
            "--seed", str(seed),
            "--simulation-db", str(simulation_db),
            "--event-db", str(event_db),
            "--log-path", str(log_path),
        ]

        subprocess.run(command, check=True)

    return pending
