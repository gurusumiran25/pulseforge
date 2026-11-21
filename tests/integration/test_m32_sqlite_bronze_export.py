"""M32: snapshot handoff from consumer SQLite storage to dbt-compatible CSV."""
import csv

import pytest

from services.analytics.bronze_export import FIELDS, export_bronze
from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


def test_export_is_deduplicated_and_replaces_snapshot(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    events = generate_customer_journey(seed=42)
    assert store.insert_events_bulk(events)["inserted"] == len(events)
    assert store.insert_events_bulk(events)["duplicates"] == len(events)
    output = tmp_path / "bronze.csv"
    assert export_bronze(store.db_path, output) == len(events)
    first = output.read_bytes()
    assert export_bronze(store.db_path, output) == len(events)
    assert output.read_bytes() == first
    with output.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert tuple(reader.fieldnames) == FIELDS
        rows = list(reader)
    assert len(rows) == len(events)
    assert len({row["event_id"] for row in rows}) == len(events)


def test_missing_database_does_not_create_one(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        export_bronze(missing, tmp_path / "bronze.csv")
    assert not missing.exists()


def test_rejects_source_database_as_output(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    with pytest.raises(ValueError):
        export_bronze(store.db_path, store.db_path)
