"""Daily synthetic public feed with real dbt quality gating.

Builds an isolated 14-day rolling synthetic dataset, verifies Bronze and dbt,
then atomically replaces public artifacts on the runner. GitHub Actions commits
both files in one git commit only after all validation succeeds.
"""
import argparse
import json
import os
import shutil
import tempfile
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from apps.dashboard.metrics import load_events, summarize
from services.analytics.bronze_manifest import verify_manifest
from services.analytics.warehouse_health import check_warehouse
from services.analytics.warehouse_run_report import run_reported_batch
from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


def build_public_feed(output_dir, *, as_of=None, days=14, sessions_per_day=40):
    if not 1 <= days <= 31 or not 1 <= sessions_per_day <= 200:
        raise ValueError("days must be 1..31 and sessions_per_day 1..200")
    day = as_of or datetime.now(timezone.utc).date()
    if not isinstance(day, date):
        raise TypeError("as_of must be a date")
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pulseforge-daily-") as temp:
        workspace = Path(temp)
        store = SQLiteEventStore(workspace / "events.db")
        for offset in range(days):
            cohort = day - timedelta(days=days - offset - 1)
            for index in range(sessions_per_day):
                seed = cohort.toordinal() * 1000 + index
                journey = generate_customer_journey(seed=seed)
                start = datetime.combine(cohort, time(12, 0), timezone.utc)
                shifted = [
                    event.model_copy(update={"event_time": start + timedelta(seconds=30 * i)})
                    for i, event in enumerate(journey)
                ]
                store.insert_events_bulk(shifted)
        report_path = workspace / "run-report.json"
        report = run_reported_batch(store.db_path, workspace / "build", report_path)
        health = check_warehouse(report_path)
        if not health["healthy"]:
            raise ValueError("Warehouse health gate failed: " + "; ".join(health["issues"]))
        bronze = workspace / "build/dbt/seeds/bronze_events.csv"
        manifest = workspace / "build/bronze.manifest.json"
        verified = verify_manifest(bronze, manifest)
        metrics = summarize(load_events(bronze))
        if metrics["events"] != store.count_events() or verified["rows"] != metrics["events"]:
            raise ValueError("Published data metrics mismatch")
        import duckdb
        with duckdb.connect(report["result"]["warehouse"], read_only=True) as con:
            warehouse_count = con.execute("SELECT count(*) FROM stg_events").fetchone()[0]
            paid_count = con.execute("SELECT coalesce(sum(completed_payment),0) FROM fct_session_funnel").fetchone()[0]
        if warehouse_count != metrics["events"] or paid_count != metrics["paid_sessions"]:
            raise ValueError("Warehouse/dashboard metrics mismatch")
        # Never overwrite the last healthy public dataset until the new build passes.
        for src, name in ((bronze, "latest_bronze.csv"), (manifest, "latest_bronze.manifest.json")):
            staging = target / (name + ".new")
            shutil.copyfile(src, staging)
            os.replace(staging, target / name)
        status = {"as_of_utc": day.isoformat(), "days": days, "sessions_per_day": sessions_per_day,
                  "events": metrics["events"], "sessions": metrics["sessions"],
                  "paid_sessions": metrics["paid_sessions"],
                  "quality_checks": report["result"]["quality"]["checks"],
                  "status": "passed"}
        status_temp = target / "status.json.new"
        status_temp.write_text(json.dumps(status, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(status_temp, target / "status.json")
        return status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/public")
    parser.add_argument("--as-of")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--sessions-per-day", type=int, default=40)
    args = parser.parse_args()
    print(json.dumps(build_public_feed(args.output_dir, as_of=date.fromisoformat(args.as_of) if args.as_of else None,
                                       days=args.days, sessions_per_day=args.sessions_per_day), indent=2))


if __name__ == "__main__":
    main()
