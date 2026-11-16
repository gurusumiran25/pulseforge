from datetime import date
from unittest.mock import patch

import pytest

from services.simulation.backlog_status import check_backlog_status
from services.simulation.coordinated_daily import run_coordinated_daily
from services.simulation.run_logger import write_run_log


def make_args(tmp_path):
    return {
        "log_path": tmp_path / "runs.jsonl",
        "simulation_db": tmp_path / "customers.db",
        "event_db": tmp_path / "events.db",
        "customers": 20,
        "seed": 42,
        "max_days": 7,
        "today": date(2026, 11, 20),
    }


def test_incomplete_backlog_raises(tmp_path):
    args = make_args(tmp_path)

    for day in range(13, 20):
        write_run_log(
            args["log_path"],
            "completed",
            f"2026-11-{day:02d}",
        )

    with patch(
        "services.simulation.coordinated_daily.run_safe_recovery",
        return_value=[],
    ):
        with pytest.raises(RuntimeError, match="backlog incomplete"):
            run_coordinated_daily(**args, execute=True)


def test_complete_backlog_succeeds(tmp_path):
    args = make_args(tmp_path)

    for day in range(13, 21):
        write_run_log(
            args["log_path"],
            "completed",
            f"2026-11-{day:02d}",
        )

    with patch(
        "services.simulation.coordinated_daily.run_safe_recovery",
        return_value=[],
    ):
        assert run_coordinated_daily(**args, execute=True) == []


def test_preview_does_not_require_completed_backlog(tmp_path):
    args = make_args(tmp_path)

    with patch(
        "services.simulation.coordinated_daily.run_safe_recovery",
        return_value=[],
    ) as recovery:
        assert run_coordinated_daily(**args, execute=False) == []
        assert recovery.call_args.kwargs["execute"] is False


def test_completed_today_does_not_hide_earlier_gap(tmp_path):
    args = make_args(tmp_path)

    write_run_log(
        args["log_path"],
        "completed",
        "2026-11-20",
    )

    status = check_backlog_status(
        args["log_path"],
        "2026-11-13",
        "2026-11-20",
    )

    assert status["target_completed"] is True
    assert status["fully_caught_up"] is False
    assert status["pending_count"] == 7
