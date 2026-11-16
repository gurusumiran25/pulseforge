"""Safe quality-report refresh for PulseForge M18."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from services.quality.report import generate_report


def refresh_quality(
    event_db="data/automation/events.db",
    customer_db="data/automation/customers.db",
    report_dir="reports/quality",
    execute=False,
):
    report = generate_report(event_db, customer_db)

    result = {
        "mode": "EXECUTE" if execute else "PREVIEW",
        "status": report["status"],
        "total_events": report["total_events"],
        "total_issues": report["total_issues"],
        "quality_score": report["quality_score"],
        "quality_grade": report["quality_grade"],
        "report_path": None,
        "persisted": False,
    }

    if not execute:
        return result

    directory = Path(report_dir)
    directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    destination = directory / f"quality_{timestamp}.json"

    with destination.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, allow_nan=False)

    result["report_path"] = str(destination)
    result["persisted"] = True

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    result = refresh_quality(execute=args.execute)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
