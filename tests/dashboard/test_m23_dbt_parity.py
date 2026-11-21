"""Verify dashboard calculations against actual dbt-built marts.

This test is intentionally skipped in standard pytest unless M23_DBT_PARITY_DB
points to the disposable DuckDB database built in CI.
"""
import os
from pathlib import Path

import pytest

from apps.dashboard.metrics import load_events, summarize


def test_dashboard_matches_dbt_marts():
    path = os.environ.get("M23_DBT_PARITY_DB")
    if not path:
        pytest.skip("Set M23_DBT_PARITY_DB to a disposable dbt DuckDB output")
    duckdb = pytest.importorskip("duckdb")
    assert Path(path).is_file(), "Expected disposable dbt warehouse database"
    dashboard = summarize(load_events())
    con = duckdb.connect(path, read_only=True)
    try:
        daily = con.execute(
            "select cast(cohort_date_utc as varchar), sessions, "
            "sessions_with_product_view, sessions_with_cart, "
            "sessions_with_checkout, sessions_with_payment "
            "from agg_daily_funnel order by cohort_date_utc"
        ).fetchall()
        session = con.execute(
            "select count(*), coalesce(sum(completed_payment),0) from fct_session_funnel"
        ).fetchone()
        activity = con.execute(
            "select cast(activity_date_utc as varchar), sum(events), count(distinct user_id) "
            "from agg_daily_user_activity group by 1 order by 1"
        ).fetchall()
    finally:
        con.close()
    assert session == (dashboard["sessions"], dashboard["paid_sessions"])
    assert daily == [
        (row["date"], row["sessions"], row["product_viewed"], row["add_to_cart"],
         row["checkout_started"], row["payment_succeeded"])
        for row in dashboard["daily_funnel"]
    ]
    assert activity == [
        (row["date"], row["events"], row["active_users"])
        for row in dashboard["daily_activity"]
    ]
