import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.simulation.safe_recovery import run_safe_recovery


AUTOMATION_START_DATE = "2026-11-13"


def run_coordinated_daily(
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
        ist = timezone(timedelta(hours=5, minutes=30))
        today = datetime.now(ist).date()

    result = run_safe_recovery(
        start_date=AUTOMATION_START_DATE,
        end_date=today.isoformat(),
        log_path=log_path,
        simulation_db=simulation_db,
        event_db=event_db,
        customers=customers,
        seed=seed,
        max_days=max_days,
        execute=execute,
    )

    if execute:
        from services.simulation.backlog_status import check_backlog_status

        health = check_backlog_status(
            log_path,
            AUTOMATION_START_DATE,
            today.isoformat(),
        )

        if not health["fully_caught_up"]:
            raise RuntimeError(
                "PulseForge backlog incomplete: "
                f'{health["pending_count"]} pending dates; '
                f'oldest={health["oldest_pending"]}'
            )

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--customers", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-days", type=int, default=7)
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

    result = run_coordinated_daily(
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
