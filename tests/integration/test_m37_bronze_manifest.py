"""M37 manifest integrity and recovery detection."""
import json

import pytest

from services.analytics.bronze_manifest import verify_manifest, write_manifest
from services.analytics.incremental_bronze import refresh_bronze
from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


def test_manifest_roundtrip_and_repeatable_verification(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    store.insert_events_bulk(generate_customer_journey(seed=42))
    csv_path, manifest_path = tmp_path / "bronze.csv", tmp_path / "bronze.manifest.json"
    refresh_bronze(store.db_path, csv_path)
    manifest = write_manifest(csv_path, manifest_path)
    assert manifest["rows"] == store.count_events()
    assert verify_manifest(csv_path, manifest_path)["sha256"] == manifest["sha256"]


def test_detects_changed_snapshot_after_manifest_creation(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    store.insert_events_bulk(generate_customer_journey(seed=42))
    csv_path, manifest_path = tmp_path / "bronze.csv", tmp_path / "bronze.manifest.json"
    refresh_bronze(store.db_path, csv_path)
    write_manifest(csv_path, manifest_path)
    store.insert_events_bulk(generate_customer_journey(seed=43))
    refresh_bronze(store.db_path, csv_path)
    with pytest.raises(ValueError, match="does not match"):
        verify_manifest(csv_path, manifest_path)
    write_manifest(csv_path, manifest_path)
    assert verify_manifest(csv_path, manifest_path)["rows"] == store.count_events()


def test_detects_tampering_and_unsupported_version(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    store.insert_events_bulk(generate_customer_journey(seed=42))
    csv_path, manifest_path = tmp_path / "bronze.csv", tmp_path / "bronze.manifest.json"
    refresh_bronze(store.db_path, csv_path)
    write_manifest(csv_path, manifest_path)
    csv_path.write_bytes(csv_path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="does not match"):
        verify_manifest(csv_path, manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = 99
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="version"):
        verify_manifest(csv_path, manifest_path)
