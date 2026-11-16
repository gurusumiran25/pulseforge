import sqlite3
from datetime import datetime, timezone

import pytest

from services.simulation.atomic_daily_selector import AtomicDailySelector
from services.simulation.daily_orchestrator import DailySimulationOrchestrator


DAY = datetime(2026, 11, 2, tzinfo=timezone.utc)


def test_same_seed_retry_is_idempotent(tmp_path):
    runner = DailySimulationOrchestrator(
        tmp_path / "simulation.db",
        tmp_path / "events.db",
    )

    first = runner.run(DAY, 20, seed=42)
    retry = runner.run(DAY, 20, seed=42)

    assert first.newly_stored_events > 0
    assert retry.newly_stored_events == 0
    assert retry.events_after == first.events_after


def test_different_seed_is_rejected(tmp_path):
    runner = DailySimulationOrchestrator(
        tmp_path / "simulation.db",
        tmp_path / "events.db",
    )

    first = runner.run(DAY, 20, seed=42)

    with pytest.raises(ValueError, match="different seed"):
        runner.run(DAY, 20, seed=99)

    assert runner.event_store.count_events() == first.events_after
    assert runner.selector.count_customers() == 20


def test_seed_persists_after_restart(tmp_path):
    db = tmp_path / "simulation.db"

    first = AtomicDailySelector(db)
    original = first.select_for_day(DAY, 20, seed=42)

    restarted = AtomicDailySelector(db)
    retry = restarted.select_for_day(DAY, 20, seed=42)

    assert original.customer_ids == retry.customer_ids

    with pytest.raises(ValueError, match="different seed"):
        restarted.select_for_day(DAY, 20, seed=99)


def test_legacy_run_without_seed_is_blocked(tmp_path):
    db = tmp_path / "simulation.db"

    with sqlite3.connect(db) as connection:
        connection.execute("""
            CREATE TABLE daily_runs (
                run_date TEXT PRIMARY KEY,
                total_customers INTEGER NOT NULL,
                returning_ratio REAL NOT NULL,
                selection_json TEXT NOT NULL
            )
        """)
        connection.execute("""
            INSERT INTO daily_runs
            (run_date, total_customers, returning_ratio, selection_json)
            VALUES (?, ?, ?, ?)
        """, (
            "2026-11-02",
            20,
            0.30,
            '{"customer_ids":[],"new_customer_ids":[],"returning_customer_ids":[]}',
        ))

    selector = AtomicDailySelector(db)

    with pytest.raises(ValueError, match="no recorded seed"):
        selector.select_for_day(DAY, 20, seed=42)
