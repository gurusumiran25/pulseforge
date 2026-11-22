"""Verified GitHub feed rejects tampered and oversized content."""
import hashlib
import json

import pytest

from apps.dashboard import public_feed


def test_rejects_tampered_remote_csv(monkeypatch):
    manifest = json.dumps({"schema_version": 1, "rows": 1, "sha256": hashlib.sha256(b"correct").hexdigest()}).encode()
    def fake_download(name, limit):
        return manifest if name.endswith(".json") else b"tampered"
    monkeypatch.setattr(public_feed, "_download", fake_download)
    with pytest.raises(ValueError, match="integrity mismatch"):
        public_feed.load_verified_public_feed()


def test_rejects_unknown_schema(monkeypatch):
    monkeypatch.setattr(public_feed, "_download", lambda name, limit: b'{"schema_version":999}')
    with pytest.raises(ValueError, match="Unsupported"):
        public_feed.load_verified_public_feed()
