"""M66 public payment feed snapshot integrity regression tests."""
import csv
import hashlib
import io
import json

import pytest

from apps.dashboard import payment_feed
from services.analytics.payment_sidecar import FIELDS


def _payment_csv():
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerow({
        "event_id": "p1", "event_name": "payment_succeeded",
        "user_id": "synthetic_1", "event_time": "2026-11-23T12:00:00+00:00",
        "order_id": "o1", "amount": "20.00", "currency": "INR",
    })
    return output.getvalue().encode()


def test_verified_payment_feed_requires_matching_bronze_digest(monkeypatch):
    raw = _payment_csv()
    digest = hashlib.sha256(raw).hexdigest()
    status = {"payment_sidecar": {
        "schema_version": 1, "rows": 1, "sha256": digest, "bronze_sha256": "bronze123"
    }}
    monkeypatch.setattr(payment_feed, "_download", lambda name, limit: (
        json.dumps(status).encode() if name == "status.json" else raw
    ))
    manifest = {"sha256": "bronze123", "generated_at_utc": "2026-11-23T12:00:00+00:00"}
    rows = payment_feed.load_verified_payment_feed(manifest)
    assert rows[0]["properties"]["amount"] == "20.00"
    with pytest.raises(ValueError, match="snapshots differ"):
        payment_feed.load_verified_payment_feed({**manifest, "sha256": "other"})


def test_verified_payment_feed_rejects_tampered_csv(monkeypatch):
    raw = _payment_csv()
    status = {"payment_sidecar": {
        "schema_version": 1, "rows": 1,
        "sha256": hashlib.sha256(raw).hexdigest(), "bronze_sha256": "bronze123"
    }}
    monkeypatch.setattr(payment_feed, "_download", lambda name, limit: (
        json.dumps(status).encode() if name == "status.json" else raw.replace(b"20.00", b"90.00")
    ))
    with pytest.raises(ValueError, match="digest mismatch"):
        payment_feed.load_verified_payment_feed({
            "sha256": "bronze123", "generated_at_utc": "2026-11-23T12:00:00+00:00"
        })
