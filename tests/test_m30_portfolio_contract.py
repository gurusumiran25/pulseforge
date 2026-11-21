"""Keep portfolio evidence links and documented claims anchored to actual source."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_portfolio_evidence_paths_exist():
    expected = (
        "docs/PORTFOLIO_DEMO.md",
        "tests/integration/test_m26_real_broker_e2e.py",
        "tests/integration/test_m27_generated_dbt_parity.py",
        "tests/integration/test_m28_generated_dashboard_parity.py",
        "apps/dashboard/streamlit_app.py",
        "warehouse/dbt/dbt_project.yml",
        ".github/workflows/m26-real-broker-e2e.yml",
        ".github/workflows/m27-generated-dbt.yml",
        ".github/workflows/m28-generated-dashboard.yml",
    )
    for name in expected:
        assert (ROOT / name).is_file(), f"Portfolio evidence missing: {name}"


def test_portfolio_does_not_claim_production_deployment():
    content = (ROOT / "docs/PORTFOLIO_DEMO.md").read_text(encoding="utf-8")
    assert "not one deployed continuous production pipeline" in content
    assert "not production deployed" in content
