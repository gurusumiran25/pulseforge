from datetime import datetime, timezone, timedelta

import pytest

from services.simulation.customer_registry import CustomerRegistry
from services.simulation.customer_selector import CustomerSelector


def day(number):
    return datetime(2026, 11, number, tzinfo=timezone.utc)


def setup_selector(tmp_path):
    registry = CustomerRegistry(tmp_path / "customers.db")
    return registry, CustomerSelector(registry, seed=42)


def test_first_day_all_customers_are_new(tmp_path):
    registry, selector = setup_selector(tmp_path)

    result = selector.select_daily_customers(
        100, returning_ratio=0.30, activity_at=day(1)
    )

    assert len(result.new_customer_ids) == 100
    assert len(result.returning_customer_ids) == 0
    assert registry.count_customers() == 100


def test_second_day_reuses_existing_customers(tmp_path):
    registry, selector = setup_selector(tmp_path)

    first = selector.select_daily_customers(
        100, activity_at=day(1)
    )
    second = selector.select_daily_customers(
        100, returning_ratio=0.30, activity_at=day(2)
    )

    assert len(second.new_customer_ids) == 70
    assert len(second.returning_customer_ids) == 30
    assert set(second.returning_customer_ids).issubset(
        set(first.customer_ids)
    )
    assert registry.count_customers() == 170


def test_returning_pool_limits_selection(tmp_path):
    registry, selector = setup_selector(tmp_path)

    selector.select_daily_customers(
        5, activity_at=day(1)
    )

    result = selector.select_daily_customers(
        100, returning_ratio=0.50, activity_at=day(2)
    )

    assert len(result.returning_customer_ids) == 5
    assert len(result.new_customer_ids) == 95


def test_selected_customers_are_unique(tmp_path):
    _, selector = setup_selector(tmp_path)

    selector.select_daily_customers(
        200, activity_at=day(1)
    )

    result = selector.select_daily_customers(
        300, activity_at=day(2)
    )

    assert len(result.customer_ids) == 300
    assert len(set(result.customer_ids)) == 300


@pytest.mark.parametrize("count", [0, -1, 6001, 2.5, True])
def test_invalid_customer_counts_rejected(tmp_path, count):
    _, selector = setup_selector(tmp_path)

    with pytest.raises(ValueError, match="total_customers"):
        selector.select_daily_customers(count)


@pytest.mark.parametrize("ratio", [-0.1, 1.1])
def test_invalid_returning_ratios_rejected(tmp_path, ratio):
    _, selector = setup_selector(tmp_path)

    with pytest.raises(ValueError, match="returning_ratio"):
        selector.select_daily_customers(10, returning_ratio=ratio)


def test_naive_activity_timestamp_rejected(tmp_path):
    _, selector = setup_selector(tmp_path)

    with pytest.raises(ValueError, match="timezone-aware"):
        selector.select_daily_customers(
            10,
            activity_at=datetime(2026, 11, 1),
        )


def test_future_customers_excluded_from_historical_day(tmp_path):
    registry, selector = setup_selector(tmp_path)

    registry.register_customer("future-customer", day(10))

    result = selector.select_daily_customers(
        10, returning_ratio=1.0, activity_at=day(2)
    )

    assert "future-customer" not in result.customer_ids
    assert len(result.returning_customer_ids) == 0


def test_activity_timestamp_normalizes_to_utc(tmp_path):
    registry, selector = setup_selector(tmp_path)

    india = timezone(timedelta(hours=5, minutes=30))

    selector.select_daily_customers(
        1,
        activity_at=datetime(2026, 11, 2, 10, 0, tzinfo=india),
    )

    with registry.connect() as connection:
        row = connection.execute(
            "SELECT first_seen FROM customers"
        ).fetchone()

    assert row["first_seen"] == "2026-11-02T04:30:00+00:00"
