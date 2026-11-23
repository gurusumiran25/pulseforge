"""Verified GitHub feed rejects tampered and oversized content."""
import hashlib
import json
from datetime import datetime, timezone

import pytest

from apps.dashboard import public_feed


def test_rejects_tampered_remote_csv(monkeypatch):
    manifest = json.dumps({"schema_version": 1, "rows": 1, "sha256": hashlib.sha256(b"correct").hexdigest(), "generated_at_utc": datetime.now(timezone.utc).isoformat()}).encode()
    def fake_download(name, limit):
        return manifest if name.endswith(".json") else b"tampered"
    monkeypatch.setattr(public_feed, "_download", fake_download)
    with pytest.raises(ValueError, match="integrity mismatch"):
        public_feed.load_verified_public_feed()


def test_rejects_unknown_schema(monkeypatch):
    monkeypatch.setattr(public_feed, "_download", lambda name, limit: b'{"schema_version":999}')
    with pytest.raises(ValueError, match="Unsupported"):
        public_feed.load_verified_public_feed()


@pytest.mark.parametrize("timestamp", [None, "not-a-date", "2026-11-23T10:00:00", "2999-01-01T00:00:00+00:00"])
def test_rejects_invalid_publication_timestamp(timestamp):
    manifest = {"generated_at_utc": timestamp}
    with pytest.raises(ValueError, match="timestamp"):
        public_feed.validate_publication_timestamp(manifest)


def test_accepts_timezone_aware_publication_timestamp():
    from datetime import datetime, timezone
    now = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
    assert public_feed.validate_publication_timestamp(
        {"generated_at_utc": "2026-11-23T11:30:00Z"}, now=now
    ) == datetime(2026, 11, 23, 11, 30, tzinfo=timezone.utc)


def test_rejects_future_timestamp_with_valid_hash(monkeypatch):
    manifest = json.dumps({"schema_version": 1, "rows": 0, "sha256": hashlib.sha256(b"").hexdigest(),
                           "generated_at_utc": "2999-01-01T00:00:00+00:00"}).encode()
    monkeypatch.setattr(public_feed, "_download", lambda name, limit: manifest if name.endswith(".json") else b"")
    with pytest.raises(ValueError, match="future"):
        public_feed.load_verified_public_feed()
