from collections import Counter

import pytest

from services.simulation.customer_behavior import (
    PROFILES,
    SEGMENT_WEIGHTS,
    get_customer_behavior,
)


def test_same_customer_gets_same_profile():
    first = get_customer_behavior("customer-001")
    second = get_customer_behavior("customer-001")
    assert first == second


def test_all_profiles_have_valid_probabilities():
    for profile in PROFILES.values():
        assert 0 <= profile.purchase_probability <= 1
        assert 0 <= profile.return_probability <= 1
        assert profile.average_basket_multiplier > 0


def test_segment_weights_total_100():
    assert sum(weight for _, weight in SEGMENT_WEIGHTS) == 100


@pytest.mark.parametrize("customer_id", ["", "   ", None, 123])
def test_invalid_customer_id_rejected(customer_id):
    with pytest.raises(ValueError, match="customer_id"):
        get_customer_behavior(customer_id)


def test_all_segments_are_reachable():
    observed = {
        get_customer_behavior(f"customer-{i}").segment
        for i in range(1000)
    }
    assert observed == set(PROFILES)


def test_distribution_is_reasonably_balanced():
    counts = Counter(
        get_customer_behavior(f"customer-{i}").segment
        for i in range(10000)
    )

    expected = dict(SEGMENT_WEIGHTS)

    for segment, weight in expected.items():
        observed_pct = counts[segment] / 100
        assert abs(observed_pct - weight) < 3
