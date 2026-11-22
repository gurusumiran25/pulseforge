"""M46: health must fail when present DuckDB marts are semantically corrupt."""
import json
import os

import pytest

from services.analytics.portfolio_demo import run_portfolio_demo
from services.analytics.warehouse_health import check_warehouse


@pytest.mark.skipif(
    os.getenv("PULSEFORGE_RUN_M46_HEALTH") != "1",
    reason="Requires real dbt DuckDB integration opt-in",
)
def test_health_detects_corrupted_daily_mart(tmp_path):
    duckdb = pytest.importorskip("duckdb")
    root = tmp_path / "demo"
    result = run_portfolio_demo(root, sessions=5)
    report = root / "run-report.json"
    assert check_warehouse(report)["healthy"]
    con = duckdb.connect(result["warehouse"])
    try:
        # dbt materializes the mart as a view; replace it with a deliberately
        # corrupted base table so the semantic health gate sees invalid data.
        con.execute("CREATE TABLE corrupt_daily AS SELECT * FROM agg_daily_funnel")
        con.execute("DROP VIEW agg_daily_funnel")
        con.execute("ALTER TABLE corrupt_daily RENAME TO agg_daily_funnel")
        con.execute("UPDATE agg_daily_funnel SET sessions = sessions + 1")
    finally:
        con.close()
    unhealthy = check_warehouse(report)
    assert not unhealthy["healthy"]
    assert any("Semantic quality:" in issue for issue in unhealthy["issues"])


def test_failed_report_does_not_claim_healthy(tmp_path):
    report = tmp_path / "failed.json"
    report.write_text(json.dumps({"schema_version": 1, "status": "failure", "result": {}}), encoding="utf-8")
    result = check_warehouse(report)
    assert not result["healthy"]
    assert result["issues"]
