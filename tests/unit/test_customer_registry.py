from datetime import datetime, timezone

import pytest

from services.simulation.customer_registry import CustomerRegistry


def utc(day):
    return datetime(2026, 11, day, tzinfo=timezone.utc)


def test_new_customer_registration(tmp_path):
    registry = CustomerRegistry(tmp_path / "customers.db")

    registry.register_customer("customer-001", utc(1))

    assert registry.count_customers() == 1
    assert registry.get_customer("customer-001")["first_seen"] == utc(1).isoformat()


def test_returning_customer_not_duplicated(tmp_path):
    registry = CustomerRegistry(tmp_path / "customers.db")

    registry.register_customer("customer-001", utc(1))
    registry.register_customer("customer-001", utc(5))

    customer = registry.get_customer("customer-001")

    assert registry.count_customers() == 1
    assert customer["first_seen"] == utc(1).isoformat()
    assert customer["last_seen"] == utc(5).isoformat()


def test_out_of_order_activity_preserves_dates(tmp_path):
    registry = CustomerRegistry(tmp_path / "customers.db")

    registry.register_customer("customer-001", utc(5))
    registry.register_customer("customer-001", utc(1))
    registry.register_customer("customer-001", utc(3))

    customer = registry.get_customer("customer-001")

    assert customer["first_seen"] == utc(1).isoformat()
    assert customer["last_seen"] == utc(5).isoformat()


def test_customer_persists_after_reopening(tmp_path):
    db = tmp_path / "customers.db"

    first_registry = CustomerRegistry(db)
    first_registry.register_customer("customer-001", utc(2))

    second_registry = CustomerRegistry(db)

    assert second_registry.count_customers() == 1
    assert second_registry.get_customer("customer-001") is not None


def test_empty_customer_id_rejected(tmp_path):
    registry = CustomerRegistry(tmp_path / "customers.db")

    with pytest.raises(ValueError, match="customer_id"):
        registry.register_customer("")


def test_naive_timestamp_rejected(tmp_path):
    registry = CustomerRegistry(tmp_path / "customers.db")

    with pytest.raises(ValueError, match="timezone-aware"):
        registry.register_customer(
            "customer-001",
            datetime(2026, 11, 1)
        )


def test_unknown_customer_returns_none(tmp_path):
    registry = CustomerRegistry(tmp_path / "customers.db")

    assert registry.get_customer("missing-customer") is None


def test_mixed_timezone_offsets_are_normalized(tmp_path):
    from datetime import timedelta

    registry = CustomerRegistry(tmp_path / "customers.db")

    india = timezone(timedelta(hours=5, minutes=30))

    registry.register_customer(
        "customer-001",
        datetime(2026, 11, 5, 10, 0, tzinfo=india)
    )

    registry.register_customer(
        "customer-001",
        datetime(2026, 11, 5, 5, 0, tzinfo=timezone.utc)
    )

    customer = registry.get_customer("customer-001")

    assert customer["first_seen"] == "2026-11-05T04:30:00+00:00"
    assert customer["last_seen"] == "2026-11-05T05:00:00+00:00"
    assert registry.count_customers() == 1
