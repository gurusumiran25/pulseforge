from datetime import datetime, timezone

import pytest

from services.simulation.customer_registry import CustomerRegistry
from services.simulation.customer_selector import CustomerSelector
from services.simulation.daily_run_ledger import DailyRunLedger


def setup_ledger(tmp_path):
    registry = CustomerRegistry(tmp_path / "customers.db")
    selector = CustomerSelector(registry, seed=42)
    ledger = DailyRunLedger(tmp_path / "daily_runs.db")
    return registry, selector, ledger


def test_first_run_registers_customers(tmp_path):
    registry, selector, ledger = setup_ledger(tmp_path)

    selection = ledger.select_for_day(
        selector,
        datetime(2026, 11, 2, tzinfo=timezone.utc),
        total_customers=200,
    )

    assert len(selection.customer_ids) == 200
    assert registry.count_customers() == 200


def test_same_day_retry_reuses_selection(tmp_path):
    registry, selector, ledger = setup_ledger(tmp_path)
    day = datetime(2026, 11, 2, tzinfo=timezone.utc)

    first = ledger.select_for_day(selector, day, 200)
    second = ledger.select_for_day(selector, day, 200)

    assert first.customer_ids == second.customer_ids
    assert first.new_customer_ids == second.new_customer_ids
    assert first.returning_customer_ids == second.returning_customer_ids
    assert registry.count_customers() == 200


def test_ledger_survives_restart(tmp_path):
    registry, selector, ledger = setup_ledger(tmp_path)
    day = datetime(2026, 11, 2, tzinfo=timezone.utc)

    first = ledger.select_for_day(selector, day, 200)

    restarted = DailyRunLedger(tmp_path / "daily_runs.db")
    second = restarted.select_for_day(selector, day, 200)

    assert first.customer_ids == second.customer_ids
    assert registry.count_customers() == 200


def test_next_day_reuses_historical_customers(tmp_path):
    registry, selector, ledger = setup_ledger(tmp_path)

    day_one = datetime(2026, 11, 2, tzinfo=timezone.utc)
    day_two = datetime(2026, 11, 3, tzinfo=timezone.utc)

    first = ledger.select_for_day(selector, day_one, 200)
    second = ledger.select_for_day(selector, day_two, 200)

    assert len(first.new_customer_ids) == 200
    assert len(second.returning_customer_ids) == 60
    assert len(second.new_customer_ids) == 140
    assert registry.count_customers() == 340


def test_changed_configuration_is_rejected(tmp_path):
    _, selector, ledger = setup_ledger(tmp_path)
    day = datetime(2026, 11, 2, tzinfo=timezone.utc)

    ledger.select_for_day(selector, day, 200)

    with pytest.raises(ValueError, match="different configuration"):
        ledger.select_for_day(selector, day, 300)


def test_naive_timestamp_is_rejected(tmp_path):
    _, selector, ledger = setup_ledger(tmp_path)

    with pytest.raises(ValueError, match="timezone-aware"):
        ledger.select_for_day(
            selector,
            datetime(2026, 11, 2),
            200,
        )
