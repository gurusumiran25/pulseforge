"""Compare generated SQLite warehouse metrics against dbt-built DuckDB marts."""
import json
import os
from pathlib import Path

import pytest


def test_generated_events_match_dbt_warehouse():
    root = os.environ.get("M27_OUTPUT_DIR")
    if not root:
        pytest.skip("Requires isolated M27 generated dbt build")
    duckdb = pytest.importorskip("duckdb")
    root = Path(root)
    expected = json.loads((root / "expected.json").read_text(encoding="utf-8"))
    conn = duckdb.connect(str(root / "warehouse.duckdb"), read_only=True)
    try:
        events = conn.execute("select count(*) from stg_events").fetchone()[0]
        sessions, paid = conn.execute(
            "select count(*), coalesce(sum(completed_payment),0) from fct_session_funnel"
        ).fetchone()
        daily = conn.execute(
            "select cast(cohort_date_utc as varchar), sessions, "
            "sessions_with_product_view, sessions_with_cart, "
            "sessions_with_checkout, sessions_with_payment "
            "from agg_daily_funnel order by cohort_date_utc"
        ).fetchall()
    finally:
        conn.close()
    assert events == expected["events"]
    assert sessions == expected["sessions"]
    assert paid == expected["paid_sessions"]
    assert [list(row) for row in daily] == expected["daily"]
