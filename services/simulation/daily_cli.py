import argparse
import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from services.simulation.daily_orchestrator import DailySimulationOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="PulseForge daily customer simulation"
    )
    parser.add_argument("--date", required=True)
    parser.add_argument("--customers", type=int, required=True)
    parser.add_argument("--returning-ratio", type=float, default=0.30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--recovery-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--log-path", default="data/logs/daily_runs.jsonl")
    parser.add_argument(
        "--simulation-db",
        default="data/storage/daily_simulation.db",
    )
    parser.add_argument(
        "--event-db",
        default="data/storage/pulseforge.db",
    )

    args = parser.parse_args()

    try:
        activity_date = date.fromisoformat(args.date)
        if activity_date.isoformat() != args.date:
            raise ValueError("Date must use YYYY-MM-DD")
        if not 1 <= args.customers <= 6000:
            raise ValueError("Customers must be between 1 and 6000")
        if not 0 <= args.returning_ratio <= 1:
            raise ValueError("Returning ratio must be between 0 and 1")
        if (
            Path(args.simulation_db).resolve()
            == Path(args.event_db).resolve()
        ):
            raise ValueError("Database paths must be different")
    except ValueError as error:
        parser.error(str(error))

    activity_at = datetime(
        activity_date.year,
        activity_date.month,
        activity_date.day,
        tzinfo=timezone.utc,
    )

    configuration = {
        "date": args.date,
        "customers": args.customers,
        "returning_ratio": args.returning_ratio,
        "seed": args.seed,
        "simulation_db": args.simulation_db,
        "event_db": args.event_db,
    }

    if args.dry_run:
        print(json.dumps({
            "status": "dry_run",
            "database_writes": False,
            "configuration": configuration,
        }, indent=2))
        return

    from services.simulation.execution_lock import (
        execution_lock,
        SimulationAlreadyRunning,
    )
    from services.simulation.run_logger import write_run_log

    log_path = Path(args.log_path)

    from contextlib import nullcontext

    recovery_lock = str(Path(args.simulation_db).resolve()) + ".recovery"
    batch_guard = (
        nullcontext()
        if args.recovery_worker
        else execution_lock(recovery_lock)
    )

    try:
        with batch_guard, execution_lock(args.simulation_db):
            write_run_log(
                log_path, "started", args.date,
                {"customers": args.customers, "seed": args.seed},
            )

            try:
                runner = DailySimulationOrchestrator(
                    simulation_db_path=args.simulation_db,
                    event_db_path=args.event_db,
                )

                summary = runner.run(
                    activity_at=activity_at,
                    total_customers=args.customers,
                    returning_ratio=args.returning_ratio,
                    seed=args.seed,
                )

            except Exception as error:
                write_run_log(
                    log_path, "failed", args.date,
                    {"error": str(error)},
                )
                raise

            write_run_log(
                log_path, "completed", args.date,
                asdict(summary),
            )

    except SimulationAlreadyRunning as error:
        parser.exit(2, f"ERROR: {error}\\n")

    print(json.dumps({
        "status": "completed",
        "summary": asdict(summary),
    }, indent=2))


if __name__ == "__main__":
    main()
