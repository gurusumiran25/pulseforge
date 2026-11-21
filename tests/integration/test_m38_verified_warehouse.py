"""M38: manifest integrity is checked before any dbt command executes."""
from unittest.mock import patch

import pytest

from services.analytics.bronze_manifest import verify_manifest
from services.analytics.warehouse_batch import run_warehouse_batch
from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


def test_batch_writes_verified_manifest(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    events = generate_customer_journey(seed=42)
    store.insert_events_bulk(events)
    with patch("services.analytics.warehouse_batch.subprocess.run") as runner:
        result = run_warehouse_batch(store.db_path, tmp_path / "output")
    assert result["events_exported"] == len(events)
    assert verify_manifest(
        tmp_path / "output/dbt/seeds/bronze_events.csv", result["manifest"]
    )["rows"] == len(events)
    runner.assert_called_once()


def test_integrity_failure_prevents_dbt_execution(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    store.insert_events_bulk(generate_customer_journey(seed=42))
    with patch(
        "services.analytics.warehouse_batch.verify_manifest",
        side_effect=ValueError("Bronze integrity failure"),
    ), patch("services.analytics.warehouse_batch.subprocess.run") as runner:
        with pytest.raises(ValueError, match="integrity failure"):
            run_warehouse_batch(store.db_path, tmp_path / "output")
    runner.assert_not_called()
