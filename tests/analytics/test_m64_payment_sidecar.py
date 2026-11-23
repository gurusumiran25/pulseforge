"""M64 synthetic payment sidecar integrity tests."""
import csv
import hashlib

import pytest

from services.analytics.payment_sidecar import FIELDS, load_payment_sidecar


def fixture_csv(path):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow({
            "event_id": "e1", "event_name": "payment_succeeded",
            "user_id": "synthetic_u1", "event_time": "2026-11-23T12:00:00+00:00",
            "order_id": "o1", "amount": "100.00", "currency": "INR",
        })
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_valid_sidecar_maps_payment_properties(tmp_path):
    path = tmp_path / "payments.csv"
    sha = fixture_csv(path)
    rows = load_payment_sidecar(path, expected_sha256=sha, expected_rows=1)
    assert rows[0]["properties"]["amount"] == "100.00"
    assert rows[0]["properties"]["order_id"] == "o1"


def test_tampering_fails_closed(tmp_path):
    path = tmp_path / "payments.csv"
    sha = fixture_csv(path)
    path.write_bytes(path.read_bytes().replace(b"100.00", b"900.00"))
    with pytest.raises(ValueError, match="SHA-256"):
        load_payment_sidecar(path, expected_sha256=sha, expected_rows=1)


def test_wrong_count_fails_closed(tmp_path):
    path = tmp_path / "payments.csv"
    sha = fixture_csv(path)
    with pytest.raises(ValueError, match="row count"):
        load_payment_sidecar(path, expected_sha256=sha, expected_rows=2)


def test_duplicate_event_id_fails_closed(tmp_path):
    path = tmp_path / "payments.csv"
    fixture_csv(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("e1,payment_succeeded,synthetic_u1,2026-11-23T12:00:00+00:00,o2,10,INR\n")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Duplicate"):
        load_payment_sidecar(path, expected_sha256=sha, expected_rows=2)
