"""M40 bounded retry semantics and isolation."""
import subprocess
from unittest.mock import patch

import pytest

from services.analytics.warehouse_retry import run_with_retries
from services.storage.sqlite_store import SQLiteEventStore


def test_retry_transient_dbt_failure_then_succeed(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    root = tmp_path / "attempts"
    failure = subprocess.CalledProcessError(1, ["dbt", "build"])
    with patch("services.analytics.warehouse_retry.run_reported_batch",
               side_effect=[failure, {"status": "success", "run_id": "test"}]) as run:
        result = run_with_retries(store.db_path, root, max_attempts=3)
    assert result["status"] == "success"
    assert run.call_count == 2
    assert run.call_args_list[0].args[1] == root / "attempt-1"
    assert run.call_args_list[1].args[1] == root / "attempt-2"


def test_integrity_error_never_retries(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    with patch("services.analytics.warehouse_retry.run_reported_batch",
               side_effect=ValueError("Bronze integrity failure")) as run:
        with pytest.raises(ValueError, match="integrity"):
            run_with_retries(store.db_path, tmp_path / "attempts")
    run.assert_called_once()


def test_retries_are_bounded(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    failure = subprocess.TimeoutExpired(["dbt", "build"], timeout=1)
    with patch("services.analytics.warehouse_retry.run_reported_batch",
               side_effect=failure) as run:
        with pytest.raises(subprocess.TimeoutExpired):
            run_with_retries(store.db_path, tmp_path / "attempts", max_attempts=2)
    assert run.call_count == 2


def test_refuses_existing_output_and_source_containment(tmp_path):
    store = SQLiteEventStore(tmp_path / "events.db")
    root = tmp_path / "attempts"
    root.mkdir()
    (root / "existing.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        run_with_retries(store.db_path, root)
    assert (root / "existing.txt").read_text(encoding="utf-8") == "keep"
    with pytest.raises(ValueError, match="source"):
        run_with_retries(store.db_path, tmp_path)


def test_invalid_attempt_count(tmp_path):
    with pytest.raises(ValueError, match="max_attempts"):
        run_with_retries(tmp_path / "missing.db", tmp_path / "attempts", max_attempts=0)
