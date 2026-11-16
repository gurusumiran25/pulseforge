import pytest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from services.simulation.safe_recovery import run_safe_recovery
from services.simulation.execution_lock import (
    execution_lock,
    SimulationAlreadyRunning,
)
from services.simulation.run_health import check_run


def test_recovery_preview_and_execution(tmp_path):
    args = dict(
        start_date="2026-11-10",
        end_date="2026-11-12",
        log_path=tmp_path / "runs.jsonl",
        simulation_db=tmp_path / "customers.db",
        event_db=tmp_path / "events.db",
        customers=20,
        seed=42,
        max_days=7,
    )

    with patch(
        "services.simulation.ordered_recovery.datetime"
    ) as clock:
        from datetime import datetime, timedelta, timezone

        clock.now.return_value = datetime(
            2026, 11, 13, 12, 0,
            tzinfo=timezone(timedelta(hours=5, minutes=30))
        )

        pending = run_safe_recovery(**args, execute=False)

        assert [item["date"] for item in pending] == [
            "2026-11-10",
            "2026-11-11",
            "2026-11-12",
        ]

        recovered = run_safe_recovery(**args, execute=True)
        assert len(recovered) == 3

        for day in [
            "2026-11-10",
            "2026-11-11",
            "2026-11-12",
        ]:
            assert check_run(args["log_path"], day)["status"] == "completed"

        assert run_safe_recovery(**args, execute=True) == []


def test_recovery_batch_lock(tmp_path):
    db = tmp_path / "customers.db"
    lock_target = str(db.resolve()) + ".recovery"

    with execution_lock(lock_target):
        with pytest.raises(SimulationAlreadyRunning):
            run_safe_recovery(
                start_date="2026-11-10",
                end_date="2026-11-12",
                log_path=tmp_path / "runs.jsonl",
                simulation_db=db,
                event_db=tmp_path / "events.db",
            )


def test_recovery_rejects_same_database(tmp_path):
    db = tmp_path / "same.db"

    with pytest.raises(ValueError):
        run_safe_recovery(
            start_date="2026-11-10",
            end_date="2026-11-12",
            log_path=tmp_path / "runs.jsonl",
            simulation_db=db,
            event_db=db,
        )


def test_recovery_rejects_oversized_batch(tmp_path):
    with pytest.raises(ValueError):
        run_safe_recovery(
            start_date="2026-11-10",
            end_date="2026-11-12",
            log_path=tmp_path / "runs.jsonl",
            simulation_db=tmp_path / "customers.db",
            event_db=tmp_path / "events.db",
            max_days=8,
        )
