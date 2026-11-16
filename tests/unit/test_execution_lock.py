import subprocess
import sys

from services.simulation.execution_lock import (
    SimulationAlreadyRunning,
    execution_lock,
)


WORKER = """
import sys
from services.simulation.execution_lock import execution_lock

with execution_lock(sys.argv[1]):
    print("LOCK_ACQUIRED", flush=True)
    sys.stdin.readline()
"""


def start_worker(db_path):
    worker = subprocess.Popen(
        [sys.executable, "-c", WORKER, str(db_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Timeout protection for startup is handled by the test runner.
        assert worker.stdout.readline().strip() == "LOCK_ACQUIRED"
        return worker
    except BaseException:
        worker.kill()
        worker.communicate(timeout=10)
        raise


def test_separate_process_cannot_acquire_same_lock(tmp_path):
    db = tmp_path / "simulation.db"
    worker = start_worker(db)

    try:
        try:
            with execution_lock(db):
                raise AssertionError("Overlapping execution was allowed")
        except SimulationAlreadyRunning:
            pass
    finally:
        if worker.poll() is None:
            worker.stdin.write("\n")
            worker.stdin.flush()
        worker.communicate(timeout=10)

    with execution_lock(db):
        pass


def test_lock_released_after_forced_termination(tmp_path):
    db = tmp_path / "simulation.db"
    worker = start_worker(db)

    try:
        worker.kill()
        worker.communicate(timeout=10)

        with execution_lock(db):
            pass
    finally:
        if worker.poll() is None:
            worker.kill()
            worker.communicate(timeout=10)


import pytest


def test_lock_released_after_exception(tmp_path):
    db = tmp_path / "exception.db"

    with pytest.raises(ValueError, match="intentional"):
        with execution_lock(db):
            raise ValueError("intentional")

    with execution_lock(db):
        pass


def test_lock_can_be_acquired_repeatedly(tmp_path):
    db = tmp_path / "repeated.db"

    for _ in range(5):
        with execution_lock(db):
            pass


def test_nested_acquisition_is_rejected(tmp_path):
    db = tmp_path / "nested.db"

    with execution_lock(db):
        with pytest.raises(SimulationAlreadyRunning):
            with execution_lock(db):
                pytest.fail("Nested lock acquisition succeeded")


def test_distinct_database_locks_are_independent(tmp_path):
    first = tmp_path / "first.db"
    second = tmp_path / "second.db"

    with execution_lock(first):
        with execution_lock(second):
            pass
