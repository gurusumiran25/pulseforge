"""M53 daily synthetic feed acceptance and integrity checks."""
import json
import os

import pytest

from apps.dashboard.metrics import load_events, summarize
from services.analytics.bronze_manifest import verify_manifest
from services.analytics.daily_public_feed import build_public_feed


def test_rejects_invalid_parameters(tmp_path):
    with pytest.raises(ValueError):
        build_public_feed(tmp_path, days=0)
    with pytest.raises(ValueError):
        build_public_feed(tmp_path, sessions_per_day=0)


@pytest.mark.skipif(os.getenv("PULSEFORGE_RUN_M53_DAILY") != "1", reason="Real dbt integration opt-in")
def test_daily_publication_quality_and_dates(tmp_path):
    from datetime import date
    root = tmp_path / "public"
    result = build_public_feed(root, as_of=date(2026, 11, 22), days=3, sessions_per_day=4)
    assert result["status"] == "passed"
    assert result["sessions"] == 12
    csv_path = root / "latest_bronze.csv"
    manifest_path = root / "latest_bronze.manifest.json"
    assert verify_manifest(csv_path, manifest_path)["rows"] == result["events"]
    summary = summarize(load_events(csv_path))
    assert summary["sessions"] == 12
    assert [row["date"] for row in summary["daily_funnel"]] == [
        "2026-11-20", "2026-11-21", "2026-11-22"
    ]
    assert json.loads((root / "status.json").read_text())["events"] == result["events"]
