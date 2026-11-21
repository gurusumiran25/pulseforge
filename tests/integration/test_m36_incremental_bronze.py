"""M36 idempotent Bronze refresh and safety invariants."""
import csv

import pytest

from services.analytics.incremental_bronze import refresh_bronze
from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


def test_incremental_refresh_is_idempotent_and_includes_late_batches(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    csv_path = tmp_path / "bronze.csv"
    first = generate_customer_journey(seed=42)
    second = generate_customer_journey(seed=43)
    store.insert_events_bulk(first)
    assert refresh_bronze(store.db_path, csv_path) == {"total": len(first), "added": len(first)}
    initial = csv_path.read_bytes()
    assert refresh_bronze(store.db_path, csv_path) == {"total": len(first), "added": 0}
    assert csv_path.read_bytes() == initial
    store.insert_events_bulk(second)
    expected = store.count_events()
    assert refresh_bronze(store.db_path, csv_path) == {
        "total": expected, "added": expected - len(first)
    }
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == expected
    assert len({row["event_id"] for row in rows}) == expected


def test_rejects_corrupt_existing_snapshot_without_overwriting(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    output = tmp_path / "bronze.csv"
    output.write_text("event_id,event_name\nbad,row\n", encoding="utf-8")
    before = output.read_bytes()
    with pytest.raises(ValueError, match="schema"):
        refresh_bronze(store.db_path, output)
    assert output.read_bytes() == before


def test_missing_source_is_not_created(tmp_path):
    source = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        refresh_bronze(source, tmp_path / "bronze.csv")
    assert not source.exists()
