"""Real dbt acceptance test for the one-command synthetic portfolio demo."""
import os

import pytest

from services.analytics.portfolio_demo import run_portfolio_demo


def test_refuses_existing_output_without_overwriting(tmp_path):
    root = tmp_path / "demo"
    root.mkdir()
    existing = root / "keep.txt"
    existing.write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError):
        run_portfolio_demo(root)
    assert existing.read_text(encoding="utf-8") == "preserve"


def test_rejects_invalid_session_count(tmp_path):
    with pytest.raises(ValueError, match="sessions"):
        run_portfolio_demo(tmp_path / "demo", sessions=0)


@pytest.mark.skipif(
    os.getenv("PULSEFORGE_RUN_M45_DEMO") != "1",
    reason="Requires real dbt-duckdb and portfolio integration opt-in",
)
def test_real_demo_checks_all_metric_parity(tmp_path):
    pytest.importorskip("duckdb")
    result = run_portfolio_demo(tmp_path / "demo", sessions=10)
    assert result["status"] == "passed"
    assert result["sessions"] == 10
    assert result["events"] >= 30
    assert result["health"]["healthy"]
    assert result["warehouse_quality_checks"] == 8
    assert (tmp_path / "demo/demo-summary.json").is_file()
