import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
from zoneinfo import ZoneInfo

from services.simulation.recovery_planner import plan_recovery


def recover(
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
    # Allow deterministic tests without relying on the system clock.
    if today is None:
        # Windows installations may lack IANA time-zone data.
        from datetime import timezone
        today = datetime.now(timezone(timedelta(hours=5, minutes=30))).date()

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    if start > today:
        return []

    end = min(end, today)

    pending = plan_recovery(
        log_path=log_path,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        max_days=max_days,
    )

    if not execute:
        return pending

    for item in pending:
        command = [
            sys.executable,
            "-m",
            "services.simulation.daily_cli",
            "--date", item["date"],
            "--customers", str(customers),
            "--seed", str(seed),
            "--simulation-db", str(simulation_db),
            "--event-db", str(event_db),
            "--log-path", str(log_path),
        ]

        subprocess.run(command, check=True)

    return pending


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--customers", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-days", type=int, default=7)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--simulation-db",
        default="data/automation/customers.db",
    )
    parser.add_argument(
        "--event-db",
        default="data/automation/events.db",
    )
    parser.add_argument(
        "--log-path",
        default="data/automation/daily_runs.jsonl",
    )

    args = parser.parse_args()

    result = recover(
        start_date=args.start_date,
        end_date=args.end_date,
        log_path=args.log_path,
        simulation_db=args.simulation_db,
        event_db=args.event_db,
        customers=args.customers,
        seed=args.seed,
        max_days=args.max_days,
        execute=args.execute,
    )

    print(json.dumps({
        "mode": "execute" if args.execute else "preview",
        "dates": result,
    }, indent=2))


if __name__ == "__main__":
    main()
