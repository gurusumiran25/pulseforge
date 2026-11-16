import argparse
import json
from datetime import date
from pathlib import Path


def check_run(log_path, run_date):
    path = Path(log_path)

    if not path.exists():
        return {
            "run_date": run_date,
            "status": "missing",
            "reason": "Execution log does not exist",
        }

    records = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        if record.get("run_date") == run_date:
            records.append(record)

    if not records:
        status = "missing"
    elif records[-1].get("status") == "completed":
        status = "completed"
    elif records[-1].get("status") == "failed":
        status = "failed"
    else:
        status = "incomplete"

    return {
        "run_date": run_date,
        "status": status,
        "records_found": len(records),
        "last_record": records[-1] if records else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument(
        "--log-path",
        default="data/automation/daily_runs.jsonl",
    )
    args = parser.parse_args()

    date.fromisoformat(args.date)

    result = check_run(args.log_path, args.date)
    print(json.dumps(result, indent=2))

    if result["status"] != "completed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
