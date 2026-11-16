import subprocess
from datetime import date
from unittest.mock import patch

import pytest

from services.simulation.ordered_recovery import recover_in_order


def test_recovery_stops_after_failed_day():
    pending = [
        {"date": "2026-11-14", "status": "missing"},
        {"date": "2026-11-15", "status": "missing"},
        {"date": "2026-11-16", "status": "missing"},
    ]

    executed = []

    def fake_run(command, check):
        day = command[command.index("--date") + 1]
        executed.append(day)

        if day == "2026-11-15":
            raise subprocess.CalledProcessError(1, command)

        return subprocess.CompletedProcess(command, 0)

    with (
        patch(
            "services.simulation.ordered_recovery.plan_recovery",
            return_value=pending,
        ),
        patch(
            "services.simulation.ordered_recovery.validate_chronology",
            return_value=True,
        ),
        patch(
            "services.simulation.ordered_recovery.subprocess.run",
            side_effect=fake_run,
        ),
    ):
        with pytest.raises(subprocess.CalledProcessError):
            recover_in_order(
                start_date="2026-11-13",
                end_date="2026-11-16",
                log_path="unused.jsonl",
                simulation_db="unused_customers.db",
                event_db="unused_events.db",
                execute=True,
                today=date(2026, 11, 16),
            )

    assert executed == [
        "2026-11-14",
        "2026-11-15",
    ]

    assert "2026-11-16" not in executed
