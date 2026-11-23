"""M67 payment-sidecar publication health checks."""
import json

import pytest

from services.analytics import public_feed_health


def test_missing_required_sidecar_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(public_feed_health, "verify_manifest", lambda *args: {"rows": 2, "sha256": "bronze"})
    from datetime import datetime, timezone
    now = datetime(2026, 11, 23, 13, tzinfo=timezone.utc)
    (tmp_path / "status.json").write_text(json.dumps({
        "status": "passed", "quality_checks": 8, "as_of_utc": "2026-11-23",
        "events": 2, "paid_sessions": 1,
    }))
    (tmp_path / "latest_bronze.manifest.json").write_text(json.dumps({
        "generated_at_utc": "2026-11-23T12:00:00+00:00",
    }))
    with pytest.raises(ValueError, match="Required payment sidecar"):
        public_feed_health.verify_published_feed(tmp_path, now=now, require_payment_sidecar=True)
    assert public_feed_health.verify_published_feed(tmp_path, now=now)["healthy"]


def test_mismatched_payment_bronze_hash_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(public_feed_health, "verify_manifest", lambda *args: {"rows": 2, "sha256": "bronze"})
    from datetime import datetime, timezone
    now = datetime(2026, 11, 23, 13, tzinfo=timezone.utc)
    (tmp_path / "status.json").write_text(json.dumps({
        "status": "passed", "quality_checks": 8, "as_of_utc": "2026-11-23",
        "events": 2, "paid_sessions": 1,
        "payment_sidecar": {"schema_version": 1, "bronze_sha256": "wrong", "sha256": "x", "rows": 1},
    }))
    (tmp_path / "latest_bronze.manifest.json").write_text(json.dumps({
        "generated_at_utc": "2026-11-23T12:00:00+00:00",
    }))
    with pytest.raises(ValueError, match="not linked"):
        public_feed_health.verify_published_feed(tmp_path, now=now, require_payment_sidecar=True)
