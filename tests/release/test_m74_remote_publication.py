"""M74 remote publication smoke regression tests."""
from datetime import datetime, timezone

import pytest

from scripts import verify_remote_publication as smoke


def test_remote_snapshot_is_validated(monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        smoke, "load_verified_public_feed",
        lambda: ([{"event_name": "page_view"}], {
            "generated_at_utc": now.isoformat(),
            "sha256": "a" * 64,
        }),
    )
    monkeypatch.setattr(
        smoke, "load_verified_payment_feed",
        lambda manifest: [{"event_name": "payment_succeeded"}],
    )
    result = smoke.verify_remote_publication()
    assert result["healthy"] and result["events"] == 1
    assert result["successful_payments"] == 1


def test_empty_remote_payments_rejected(monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(
        smoke, "load_verified_public_feed",
        lambda: ([{"event_name": "page_view"}], {
            "generated_at_utc": now.isoformat(),
            "sha256": "a" * 64,
        }),
    )
    monkeypatch.setattr(smoke, "load_verified_payment_feed", lambda manifest: [])
    with pytest.raises(ValueError, match="empty"):
        smoke.verify_remote_publication()


def test_stale_remote_feed_rejected(monkeypatch):
    monkeypatch.setattr(
        smoke, "load_verified_public_feed",
        lambda: ([{"event_name": "page_view"}], {
            "generated_at_utc": "2020-01-01T00:00:00+00:00",
            "sha256": "a" * 64,
        }),
    )
    monkeypatch.setattr(
        smoke, "load_verified_payment_feed",
        lambda manifest: [{"event_name": "payment_succeeded"}],
    )
    with pytest.raises(ValueError, match="stale"):
        smoke.verify_remote_publication()
