"""M35 orchestration tests with a disposable SQLite database."""
from pathlib import Path
from unittest.mock import patch

import pytest

from services.analytics.warehouse_batch import run_warehouse_batch
from services.generator.journey_generator import generate_customer_journey
from services.storage.sqlite_store import SQLiteEventStore


def test_builds_isolated_snapshot_and_invokes_dbt(tmp_path):
    source = SQLiteEventStore(tmp_path / "events.db")
    events = generate_customer_journey(seed=42)
    source.insert_events_bulk(events)
    workspace = tmp_path / "build"
    with patch("services.analytics.warehouse_batch.check_quality", return_value={"healthy": True, "issues": [], "checks": 8}), \
         patch("services.analytics.warehouse_batch.subprocess.run") as command:
        result = run_warehouse_batch(source.db_path, workspace)
    assert result["events_exported"] == len(events)
    assert result["warehouse"] == str(workspace / "warehouse.duckdb")
    assert (workspace / "dbt/seeds/bronze_events.csv").is_file()
    assert (workspace / "dbt/profiles.yml").is_file()
    command.assert_called_once()
    assert command.call_args.kwargs["check"] is True
    assert command.call_args.kwargs["cwd"] == workspace / "dbt"


def test_rejects_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_warehouse_batch(tmp_path / "missing.db", tmp_path / "build")


def test_rejects_nonempty_workspace_without_overwriting(tmp_path):
    source = SQLiteEventStore(tmp_path / "events.db")
    workspace = tmp_path / "build"
    workspace.mkdir()
    existing = workspace / "keep.txt"
    existing.write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(FileExistsError):
        run_warehouse_batch(source.db_path, workspace)
    assert existing.read_text(encoding="utf-8") == "do not overwrite"


def test_rejects_workspace_containing_source(tmp_path):
    source = SQLiteEventStore(tmp_path / "events.db")
    with pytest.raises(ValueError):
        run_warehouse_batch(source.db_path, tmp_path)
