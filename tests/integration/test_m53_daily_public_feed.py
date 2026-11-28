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
    bi_root = tmp_path / "bi"
    result = build_public_feed(root, as_of=date(2026, 11, 22), days=3, sessions_per_day=4, bi_output_dir=bi_root)
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

    import csv
    import hashlib
    pointer = json.loads((bi_root / "current.json").read_text())
    snapshot = bi_root / pointer["snapshot"]
    manifest_bytes = (snapshot / "manifest.json").read_bytes()
    assert hashlib.sha256(manifest_bytes).hexdigest() == pointer["snapshot"]
    manifest = json.loads(manifest_bytes)
    assert len(manifest["files"]) == 9
    for name, metadata in manifest["files"].items():
        raw = (snapshot / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == metadata["sha256"]
        assert len(raw) == metadata["bytes"]
    with (snapshot / "FactSession.csv").open(newline="") as handle:
        sessions = list(csv.DictReader(handle))
    assert len(sessions) == result["sessions"]
    assert sum(int(row["completed_payment"]) for row in sessions) == result["paid_sessions"]
    with (snapshot / "FactEvent.csv").open(newline="") as handle:
        assert len(list(csv.DictReader(handle))) == result["events"]

    with (snapshot / "FactProductView.csv").open(newline="") as handle:
        views = list(csv.DictReader(handle))
    with (snapshot / "FactEvent.csv").open(newline="") as handle:
        expected = {r["event_id"] for r in csv.DictReader(handle) if r["event_name"] == "product_viewed"}
    assert {r["event_id"] for r in views} == expected
    assert len(views) == len(expected)
    with (snapshot / "DimProduct.csv").open(newline="") as handle:
        products = {r["product_id"] for r in csv.DictReader(handle)}
    assert all(r["product_id"] in products for r in views)


    # M92: verify the same pinned snapshot through all reference gates.
    from datetime import datetime, timezone

    from services.analytics.bi_acceptance import expected_evidence
    from services.analytics.bi_kpis import reference_kpis
    from services.analytics.bi_navigation import load_layout, validate_layout
    from services.analytics.bi_refresh import verify_refresh
    from services.analytics.bi_report import load_report, validate_report

    verified = verify_refresh(bi_root, now=datetime(2026, 11, 23, tzinfo=timezone.utc))
    assert verified["snapshot"] == pointer["snapshot"]
    tables = {name: (snapshot / name).read_bytes() for name in manifest["files"]}
    kpis = reference_kpis(tables)
    assert kpis["events"] == result["events"]
    assert kpis["sessions"] == result["sessions"]
    assert kpis["paid_sessions"] == result["paid_sessions"]
    evidence = expected_evidence(bi_root, now=datetime(2026, 11, 23, tzinfo=timezone.utc))
    assert evidence["snapshot"] == pointer["snapshot"]
    assert evidence["unfiltered"] == kpis
    assert evidence["by_currency"]
    for currency, values in evidence["by_currency"].items():
        assert values == reference_kpis(tables, currency)
    output = os.getenv("PULSEFORGE_ACCEPTANCE_OUTPUT")
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            json.dump(evidence, handle, indent=2, default=str)
    bundle = os.getenv("PULSEFORGE_ACCEPTANCE_BUNDLE")
    if bundle:
        import shutil
        from pathlib import Path

        from services.analytics.bi_pbip import write_package

        destination = Path(bundle)
        destination.mkdir(parents=True, exist_ok=False)
        shutil.copytree(bi_root, destination / "snapshot")
        write_package(destination / "PulseForge", snapshot_id=pointer["snapshot"])
        (destination / "expected-kpis.json").write_text(
            json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    assert validate_report(load_report()) == 24
    assert validate_layout(load_layout(), load_report()) == 7
    # A corrupted immutable file must prevent refresh, without changing the pointer.
    (snapshot / "FactEvent.csv").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        verify_refresh(bi_root, now=datetime(2026, 11, 23, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="integrity"):
        expected_evidence(bi_root, now=datetime(2026, 11, 23, tzinfo=timezone.utc))
    assert json.loads((bi_root / "current.json").read_text()) == pointer
