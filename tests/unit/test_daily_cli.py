import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "services.simulation.daily_cli",
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_dry_run_does_not_create_databases(tmp_path):
    simulation_db = tmp_path / "simulation.db"
    event_db = tmp_path / "events.db"

    result = run_cli(
        "--date", "2026-11-14",
        "--customers", "500",
        "--dry-run",
        "--simulation-db", str(simulation_db),
        "--event-db", str(event_db),
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["database_writes"] is False
    assert not simulation_db.exists()
    assert not event_db.exists()


def test_invalid_customer_count_is_rejected():
    result = run_cli(
        "--date", "2026-11-14",
        "--customers", "6001",
        "--dry-run",
    )

    assert result.returncode != 0
    assert "between 1 and 6000" in result.stderr


def test_invalid_date_is_rejected():
    result = run_cli(
        "--date", "2026-02-30",
        "--customers", "500",
        "--dry-run",
    )

    assert result.returncode != 0


def test_same_database_path_is_rejected(tmp_path):
    db_path = tmp_path / "shared.db"

    result = run_cli(
        "--date", "2026-11-14",
        "--customers", "500",
        "--dry-run",
        "--simulation-db", str(db_path),
        "--event-db", str(db_path),
    )

    assert result.returncode != 0
    assert not db_path.exists()


def test_actual_cli_execution_and_retry(tmp_path):
    simulation_db = tmp_path / "simulation.db"
    event_db = tmp_path / "events.db"

    args = (
        "--date", "2026-11-14",
        "--customers", "20",
        "--seed", "42",
        "--simulation-db", str(simulation_db),
        "--event-db", str(event_db),
    )

    first = run_cli(*args)
    assert first.returncode == 0, first.stderr

    first_summary = json.loads(first.stdout)["summary"]
    assert first_summary["customers"] == 20
    assert first_summary["newly_stored_events"] > 0

    second = run_cli(*args)
    assert second.returncode == 0, second.stderr

    second_summary = json.loads(second.stdout)["summary"]
    assert second_summary["newly_stored_events"] == 0
    assert second_summary["events_after"] == first_summary["events_after"]
