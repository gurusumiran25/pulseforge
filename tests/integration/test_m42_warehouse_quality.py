"""M42 DuckDB semantic data quality gates."""
import pytest

duckdb = pytest.importorskip("duckdb")

from services.analytics.warehouse_quality import check_quality


def _warehouse(path):
    con = duckdb.connect(str(path))
    con.execute("""
        CREATE TABLE stg_events AS SELECT * FROM (
            VALUES ('e1','product_viewed','s1','u1',timestamp '2026-01-01 10:00:00'),
                   ('e2','payment_succeeded','s1','u1',timestamp '2026-01-01 10:01:00')
        ) t(event_id,event_name,session_id,user_id,event_time)
    """)
    con.execute("""
        CREATE TABLE fct_session_funnel AS
        SELECT 's1' AS session_id, timestamp '2026-01-01 10:00:00' AS first_event_time,
            timestamp '2026-01-01 10:01:00' AS last_event_time,
            2 AS event_count, 1 AS viewed_product, 0 AS added_to_cart,
            0 AS started_checkout, 1 AS completed_payment
    """)
    con.execute("""
        CREATE TABLE agg_daily_funnel AS
        SELECT date '2026-01-01' AS cohort_date_utc, 1 AS sessions,
            1 AS sessions_with_product_view, 0 AS sessions_with_cart,
            0 AS sessions_with_checkout, 1 AS sessions_with_payment
    """)
    return con


def test_healthy_marts_pass(tmp_path):
    path = tmp_path / "warehouse.duckdb"
    con = _warehouse(path)
    con.close()
    assert check_quality(path) == {"healthy": True, "issues": [], "checks": 8}


def test_duplicate_event_ids_fail(tmp_path):
    path = tmp_path / "warehouse.duckdb"
    con = _warehouse(path)
    con.execute("INSERT INTO stg_events SELECT * FROM stg_events LIMIT 1")
    con.close()
    result = check_quality(path)
    assert result["healthy"] is False
    assert any("duplicate_event_ids" in issue for issue in result["issues"])


def test_mismatched_daily_aggregates_fail(tmp_path):
    path = tmp_path / "warehouse.duckdb"
    con = _warehouse(path)
    con.execute("UPDATE agg_daily_funnel SET sessions_with_payment = 0")
    con.close()
    result = check_quality(path)
    assert result["healthy"] is False
    assert any("daily_aggregate_mismatch" in issue for issue in result["issues"])


def test_missing_warehouse_rejected(tmp_path):
    with pytest.raises(FileNotFoundError):
        check_quality(tmp_path / "missing.duckdb")
