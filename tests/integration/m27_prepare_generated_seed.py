"""Generate a disposable dbt Bronze CSV and expected metrics from real SQLite views."""
import csv
import json
import sys
from pathlib import Path

from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


def main(output_dir):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    store = SQLiteEventStore(root / "events.db")
    events = [event for seed in range(30) for event in generate_customer_journey(seed=seed)]
    result = store.insert_events_bulk(events)
    assert result["inserted"] == len(events)
    sql = Path(__file__).resolve().parents[2] / "warehouse/sql/m20_views.sql"
    with store.connect() as conn:
        conn.executescript(sql.read_text(encoding="utf-8"))
        rows = conn.execute(
            "select event_id, event_name, session_id, user_id, event_time from events "
            "order by event_id"
        ).fetchall()
        sessions = conn.execute(
            "select count(*) as sessions, coalesce(sum(completed_payment),0) as paid "
            "from gold_session_funnel"
        ).fetchone()
        daily = conn.execute(
            "select cohort_date_utc, sessions, sessions_with_product_view, "
            "sessions_with_cart, sessions_with_checkout, sessions_with_payment "
            "from gold_daily_funnel order by cohort_date_utc"
        ).fetchall()
    with (root / "bronze_events.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["event_id", "event_name", "session_id", "user_id", "event_time"])
        for row in rows:
            writer.writerow(list(row))
    expected = {
        "events": len(events),
        "sessions": sessions["sessions"],
        "paid_sessions": sessions["paid"],
        "daily": [list(row) for row in daily],
    }
    (root / "expected.json").write_text(json.dumps(expected), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
