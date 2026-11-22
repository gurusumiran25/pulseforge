"""Opt-in synthetic throughput smoke test; no external services or user data."""
import os
import time

import pytest

from services.analytics.bronze_export import export_bronze
from services.analytics.bronze_manifest import verify_manifest, write_manifest
from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


@pytest.mark.skipif(
    os.getenv("PULSEFORGE_RUN_M50_PERF") != "1",
    reason="Opt-in synthetic performance smoke",
)
def test_thousand_sessions_export_integrity_and_elapsed(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    started = time.monotonic()
    for seed in range(1000):
        store.insert_events_bulk(generate_customer_journey(seed=seed))
    inserted = store.count_events()
    csv_path = tmp_path / "bronze.csv"
    exported = export_bronze(store.db_path, csv_path)
    manifest_path = tmp_path / "manifest.json"
    write_manifest(csv_path, manifest_path)
    verified = verify_manifest(csv_path, manifest_path)
    elapsed = time.monotonic() - started
    assert inserted == exported == verified["rows"]
    assert inserted >= 3000
    # Loose regression budget, not a published throughput/SLA claim.
    assert elapsed < 120, f"Synthetic smoke exceeded 120s: {elapsed:.1f}s"
