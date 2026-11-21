"""M28: verify dashboard calculations against generated SQLite and dbt results.

Only enabled by dedicated CI, which creates disposable generated datasets.
"""
import json
import os
from pathlib import Path

import pytest

from apps.dashboard.metrics import load_events, summarize


def test_generated_dashboard_equals_sqlite_and_dbt():
    output = os.environ.get("M28_OUTPUT_DIR")
    if not output:
        pytest.skip("Requires generated data and dbt build from M28 CI")
    duckdb = pytest.importorskip("duckdb")
    root = Path(output)
    expected = json.loads((root / "expected.json").read_text(encoding="utf-8"))
    metrics = summarize(load_events(root / "bronze_events.csv"))
    assert metrics["events"] == expected["events"]
    assert metrics["sessions"] == expected["sessions"]
    assert metrics["paid_sessions"] == expected["paid_sessions"]
    assert [
        [row["date"], row["sessions"], row["product_viewed"], row["add_to_cart"],
         row["checkout_started"], row["payment_succeeded"]]
        for row in metrics["daily_funnel"]
    ] == expected["daily"]
    connection = duckdb.connect(str(root / "warehouse.duckdb"), read_only=True)
    try:
        dbt_daily = connection.execute(
            "select cast(cohort_date_utc as varchar), sessions, "
            "sessions_with_product_view, sessions_with_cart, "
            "sessions_with_checkout, sessions_with_payment "
            "from agg_daily_funnel order by cohort_date_utc"
        ).fetchall()
        dbt_events = connection.execute("select count(*) from stg_events").fetchone()[0]
    finally:
        connection.close()
    assert dbt_events == metrics["events"]
    assert [list(row) for row in dbt_daily] == expected["daily"]
