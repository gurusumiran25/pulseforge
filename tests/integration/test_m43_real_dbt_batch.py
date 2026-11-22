"""Real M43 SQLite -> Bronze -> dbt DuckDB -> semantic quality integration."""
import os
import shutil

import pytest

from services.analytics.warehouse_batch import run_warehouse_batch
from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


@pytest.mark.skipif(
    os.getenv("PULSEFORGE_RUN_M43_DBT") != "1",
    reason="Requires dbt-duckdb and explicit integration opt-in",
)
def test_real_dbt_build_passes_quality_gate(tmp_path):
    pytest.importorskip("duckdb")
    if not shutil.which("dbt"):
        pytest.skip("dbt executable unavailable")
    source = SQLiteEventStore(tmp_path / "events.db")
    for seed in (42, 43, 44):
        source.insert_events_bulk(generate_customer_journey(seed=seed))
    result = run_warehouse_batch(source.db_path, tmp_path / "build")
    assert result["events_exported"] == source.count_events()
    assert result["quality"]["healthy"] is True
    assert result["quality"]["checks"] == 8
