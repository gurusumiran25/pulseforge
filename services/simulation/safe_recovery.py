import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.simulation.execution_lock import execution_lock
from services.simulation.ordered_recovery import recover_in_order


def run_safe_recovery(
    start_date,
    end_date,
    log_path,
    simulation_db,
    event_db,
    customers=500,
    seed=42,
    max_days=7,
    execute=False,
):
    if not 1 <= max_days <= 7:
        raise ValueError("Recovery batch must contain 1-7 days")

    if not 1 <= customers <= 6000:
        raise ValueError("Customers must be between 1 and 6000")

    if Path(simulation_db).resolve() == Path(event_db).resolve():
        raise ValueError("Simulation and event databases must differ")

    # Separate lock shared by all recovery batches for this database.
    recovery_lock = str(Path(simulation_db).resolve()) + ".recovery"

    with execution_lock(recovery_lock):
        return recover_in_order(
            start_date=start_date,
            end_date=end_date,
            log_path=log_path,
            simulation_db=simulation_db,
            event_db=event_db,
            customers=customers,
            seed=seed,
            max_days=max_days,
            execute=execute,
        )


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

    result = run_safe_recovery(
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
