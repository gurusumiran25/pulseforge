"""Regression coverage for the published-feed health gate."""
import json
from datetime import datetime, timedelta, timezone

import pytest

from services.analytics.bronze_manifest import write_manifest
from services.analytics.public_feed_health import verify_published_feed


def published_fixture(tmp_path, now):
    csv_path = tmp_path / "latest_bronze.csv"
    csv_path.write_text("event_id,event_name,session_id,user_id,event_time\n", encoding="utf-8")
    manifest_path = tmp_path / "latest_bronze.manifest.json"
    write_manifest(csv_path, manifest_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["generated_at_utc"] = now.isoformat()
    manifest_path.write_text(json.dumps(manifest))
    (tmp_path / "status.json").write_text(json.dumps({
        "status": "passed", "quality_checks": 8, "events": 0,
        "as_of_utc": now.date().isoformat(),
    }))
    return csv_path, manifest_path


def test_healthy_published_feed(tmp_path):
    now = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)
    published_fixture(tmp_path, now)
    assert verify_published_feed(tmp_path, now=now)["healthy"]


def test_stale_published_feed(tmp_path):
    now = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)
    published_fixture(tmp_path, now - timedelta(hours=37))
    with pytest.raises(ValueError, match="stale"):
        verify_published_feed(tmp_path, now=now)


def test_corrupted_published_csv(tmp_path):
    now = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)
    csv_path, _ = published_fixture(tmp_path, now)
    csv_path.write_text("corrupted")
    with pytest.raises(ValueError, match="schema"):
        verify_published_feed(tmp_path, now=now)


def test_failed_quality_status(tmp_path):
    now = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)
    published_fixture(tmp_path, now)
    status_path = tmp_path / "status.json"
    status = json.loads(status_path.read_text())
    status["quality_checks"] = 7
    status_path.write_text(json.dumps(status))
    with pytest.raises(ValueError, match="quality"):
        verify_published_feed(tmp_path, now=now)


def test_future_publication_rejected(tmp_path):
    now = datetime(2026, 11, 23, 12, tzinfo=timezone.utc)
    published_fixture(tmp_path, now + timedelta(hours=2))
    with pytest.raises(ValueError, match="future"):
        verify_published_feed(tmp_path, now=now)
