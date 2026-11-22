"""Incremental export and atomic directory visibility regression tests."""
import csv
import json

import pytest

from services.analytics.bronze_manifest import verify_manifest
from services.analytics.immutable_bronze_chunks import publish_chunk
from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


def test_incremental_chunks_do_not_rescan_previous_rows(tmp_path):
    store = SQLiteEventStore(tmp_path / "source.db")
    store.insert_events_bulk(generate_customer_journey(seed=1))
    first = publish_chunk(store.db_path, tmp_path / "chunks", after_rowid=0)
    assert first["rows"] == store.count_events()
    assert first["next_rowid"] > 0
    store.insert_events_bulk(generate_customer_journey(seed=2))
    second = publish_chunk(store.db_path, tmp_path / "chunks", after_rowid=first["next_rowid"])
    assert second["rows"] == store.count_events() - first["rows"]
    assert second["after_rowid"] == first["next_rowid"]
    for snapshot in (first, second):
        folder = tmp_path / "chunks" / ("after-" + f'{snapshot["after_rowid"]:020d}')
        manifest = json.loads((folder / "bronze.manifest.json").read_text())
        assert manifest["rows"] == snapshot["rows"]
        assert verify_manifest(folder / "bronze_events.csv", folder / "bronze.manifest.json")["rows"] == snapshot["rows"]
        assert json.loads((folder / "checkpoint.json").read_text())["next_rowid"] == snapshot["next_rowid"]
    with pytest.raises(FileExistsError):
        publish_chunk(store.db_path, tmp_path / "chunks", after_rowid=0)


def test_rejects_invalid_watermark_and_source_inside_destination(tmp_path):
    store = SQLiteEventStore(tmp_path / "data" / "source.db")
    with pytest.raises(ValueError):
        publish_chunk(store.db_path, tmp_path / "chunks", after_rowid=-1)
    with pytest.raises(ValueError):
        publish_chunk(store.db_path, tmp_path, after_rowid=0)


def test_empty_increment_has_only_header(tmp_path):
    store = SQLiteEventStore(tmp_path / "source.db")
    snapshot = publish_chunk(store.db_path, tmp_path / "chunks")
    assert snapshot["rows"] == 0
    with (tmp_path / "chunks" / "after-00000000000000000000" / "bronze_events.csv").open() as handle:
        assert len(list(csv.reader(handle))) == 1
