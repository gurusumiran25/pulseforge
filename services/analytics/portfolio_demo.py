"""One-command synthetic PulseForge portfolio acceptance demonstration.

Runs generator -> SQLite -> verified Bronze -> real dbt -> quality -> health ->
dashboard metric parity. Does not claim to run a live broker or web server.
"""
import argparse
import json
from pathlib import Path

from apps.dashboard.metrics import load_events, summarize
from services.analytics.warehouse_health import check_warehouse
from services.analytics.warehouse_run_report import run_reported_batch
from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


def run_portfolio_demo(output_root, *, sessions=20):
    if not 1 <= sessions <= 10000:
        raise ValueError("sessions must be between 1 and 10000")
    root = Path(output_root).resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise FileExistsError(f"Demo output directory must be empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    source = root / "events.db"
    store = SQLiteEventStore(source)
    for seed in range(sessions):
        store.insert_events_bulk(generate_customer_journey(seed=seed))
    report_path = root / "run-report.json"
    report = run_reported_batch(source, root / "build", report_path)
    health = check_warehouse(report_path)
    if not health["healthy"]:
        raise ValueError("Warehouse health gate failed: " + "; ".join(health["issues"]))
    bronze = root / "build/dbt/seeds/bronze_events.csv"
    dashboard = summarize(load_events(bronze))
    if dashboard["events"] != store.count_events():
        raise ValueError("Dashboard event count does not match SQLite")
    if dashboard["events"] != report["result"]["events_exported"]:
        raise ValueError("Dashboard event count does not match warehouse export")
    import duckdb
    warehouse = report["result"]["warehouse"]
    con = duckdb.connect(warehouse, read_only=True)
    try:
        warehouse_events = con.execute("SELECT count(*) FROM stg_events").fetchone()[0]
        warehouse_sessions = con.execute("SELECT count(*) FROM fct_session_funnel").fetchone()[0]
        warehouse_paid = con.execute(
            "SELECT coalesce(sum(completed_payment), 0) FROM fct_session_funnel"
        ).fetchone()[0]
    finally:
        con.close()
    expected = (dashboard["events"], dashboard["sessions"], dashboard["paid_sessions"])
    actual = (warehouse_events, warehouse_sessions, warehouse_paid)
    if actual != expected:
        raise ValueError(f"Warehouse/dashboard metric mismatch: {actual} != {expected}")
    result = {
        "status": "passed",
        "synthetic_sessions_requested": sessions,
        "events": dashboard["events"],
        "sessions": dashboard["sessions"],
        "paid_sessions": dashboard["paid_sessions"],
        "warehouse_quality_checks": report["result"]["quality"]["checks"],
        "health": health,
        "run_report": str(report_path),
        "bronze_csv": str(bronze),
        "warehouse": str(warehouse),
    }
    (root / "demo-summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description="Run a synthetic end-to-end portfolio demonstration")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--sessions", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(run_portfolio_demo(args.output_root, sessions=args.sessions), indent=2))


if __name__ == "__main__":
    main()
