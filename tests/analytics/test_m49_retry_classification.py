"""Ensure retry policy never repeats deterministic warehouse failures."""
import subprocess

import pytest

from services.analytics import warehouse_retry


@pytest.mark.parametrize("exc,expected", [
    (subprocess.TimeoutExpired(["dbt", "build"], 1), True),
    (subprocess.CalledProcessError(1, ["dbt", "build"]), False),
    (ValueError("manifest integrity mismatch"), False),
    (FileNotFoundError("dbt executable missing"), False),
    (RuntimeError("invalid model"), False),
])
def test_retryable_only_timeout(exc, expected):
    assert warehouse_retry.is_retryable(exc) is expected


def test_dbt_failure_never_retries(monkeypatch, tmp_path):
    source = tmp_path / "events.db"
    source.write_bytes(b"not a real db; mocked runner")
    calls = []

    def fail(*args, **kwargs):
        calls.append((args, kwargs))
        raise subprocess.CalledProcessError(1, ["dbt", "build"])

    monkeypatch.setattr(warehouse_retry, "run_reported_batch", fail)
    with pytest.raises(subprocess.CalledProcessError):
        warehouse_retry.run_with_retries(source, tmp_path / "output", max_attempts=3)
    assert len(calls) == 1


def test_timeout_is_bounded_and_isolated(monkeypatch, tmp_path):
    source = tmp_path / "events.db"
    source.write_bytes(b"mocked source")
    workspaces = []

    def fail(*args, **kwargs):
        workspaces.append(args[1])
        raise subprocess.TimeoutExpired(["dbt", "build"], 1)

    monkeypatch.setattr(warehouse_retry, "run_reported_batch", fail)
    with pytest.raises(subprocess.TimeoutExpired):
        warehouse_retry.run_with_retries(source, tmp_path / "output", max_attempts=3)
    assert len(workspaces) == 3
    assert len(set(workspaces)) == 3
