import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from services.simulation.atomic_daily_selector import AtomicDailySelector


DAY_ONE = datetime(2026, 11, 2, tzinfo=timezone.utc)
DAY_TWO = datetime(2026, 11, 3, tzinfo=timezone.utc)


def test_first_day_registers_customers(tmp_path):
    selector = AtomicDailySelector(tmp_path / "simulation.db")

    result = selector.select_for_day(DAY_ONE, 200)

    assert len(result.customer_ids) == 200
    assert selector.count_customers() == 200
    assert selector.count_daily_runs() == 1


def test_same_day_retry_does_not_duplicate(tmp_path):
    selector = AtomicDailySelector(tmp_path / "simulation.db")

    first = selector.select_for_day(DAY_ONE, 200)
    second = selector.select_for_day(DAY_ONE, 200)

    assert first.customer_ids == second.customer_ids
    assert selector.count_customers() == 200
    assert selector.count_daily_runs() == 1


def test_next_day_has_returning_customers(tmp_path):
    selector = AtomicDailySelector(tmp_path / "simulation.db")

    selector.select_for_day(DAY_ONE, 200)
    second = selector.select_for_day(DAY_TWO, 200)

    assert len(second.returning_customer_ids) == 60
    assert len(second.new_customer_ids) == 140
    assert selector.count_customers() == 340
    assert selector.count_daily_runs() == 2


def test_configuration_change_rejected(tmp_path):
    selector = AtomicDailySelector(tmp_path / "simulation.db")

    selector.select_for_day(DAY_ONE, 200)

    with pytest.raises(ValueError, match="different configuration"):
        selector.select_for_day(DAY_ONE, 300)

    assert selector.count_customers() == 200


def test_invalid_timestamp_rejected(tmp_path):
    selector = AtomicDailySelector(tmp_path / "simulation.db")

    with pytest.raises(ValueError, match="timezone-aware"):
        selector.select_for_day(datetime(2026, 11, 2), 200)


def test_database_failure_rolls_back(tmp_path):
    selector = AtomicDailySelector(tmp_path / "simulation.db")

    # A trigger deliberately interrupts customer insertion.
    # The transaction must leave no partial daily run.
    with selector.connect() as connection:
        connection.execute("""
            CREATE TRIGGER reject_customer_insert
            BEFORE INSERT ON customers
            BEGIN
                SELECT RAISE(ABORT, 'simulated database failure');
            END
        """)

    with pytest.raises(sqlite3.IntegrityError):
        selector.select_for_day(DAY_ONE, 200)

    assert selector.count_customers() == 0
    assert selector.count_daily_runs() == 0


def test_concurrent_same_day_selection(tmp_path):
    db_path = tmp_path / "simulation.db"
    selector = AtomicDailySelector(db_path)

    def worker():
        local_selector = AtomicDailySelector(db_path)
        return local_selector.select_for_day(DAY_ONE, 200).customer_ids

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker) for _ in range(2)]
        results = [future.result() for future in futures]

    assert results[0] == results[1]
    assert selector.count_customers() == 200
    assert selector.count_daily_runs() == 1


def test_restart_preserves_daily_selection(tmp_path):
    db_path = tmp_path / "simulation.db"

    first_selector = AtomicDailySelector(db_path)
    first = first_selector.select_for_day(DAY_ONE, 200)

    restarted = AtomicDailySelector(db_path)
    second = restarted.select_for_day(DAY_ONE, 200)

    assert first.customer_ids == second.customer_ids
    assert restarted.count_customers() == 200
