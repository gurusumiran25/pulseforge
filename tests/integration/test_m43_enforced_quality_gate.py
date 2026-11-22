"""M43: fail closed when a completed dbt build has invalid marts."""
from unittest.mock import patch

import pytest

from services.analytics.warehouse_batch import run_warehouse_batch
from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


def test_bad_quality_blocks_successful_batch(tmp_path):
    source = SQLiteEventStore(tmp_path / "events.db")
    source.insert_events_bulk(generate_customer_journey(seed=42))
    with patch("services.analytics.warehouse_batch.subprocess.run"), patch(
        "services.analytics.warehouse_batch.check_quality",
        return_value={"healthy": False, "issues": ["daily_aggregate_mismatch: 1"], "checks": 8},
    ):
        with pytest.raises(ValueError, match="daily_aggregate_mismatch"):
            run_warehouse_batch(source.db_path, tmp_path / "output")


def test_good_quality_is_returned_in_batch_result(tmp_path):
    source = SQLiteEventStore(tmp_path / "events.db")
    source.insert_events_bulk(generate_customer_journey(seed=42))
    quality = {"healthy": True, "issues": [], "checks": 8}
    with patch("services.analytics.warehouse_batch.subprocess.run"), patch(
        "services.analytics.warehouse_batch.check_quality", return_value=quality
    ):
        result = run_warehouse_batch(source.db_path, tmp_path / "output")
    assert result["quality"] == quality
