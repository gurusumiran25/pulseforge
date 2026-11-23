"""M60 fixed-horizon A/B testing regression tests."""
from math import isclose

import pytest

from services.analytics.experimentation import analyze_binary_experiment


def test_equal_rates_no_significance():
    result = analyze_binary_experiment(
        control_conversions=50, control_total=100,
        treatment_conversions=100, treatment_total=200,
    )
    assert result["absolute_lift"] == 0
    assert result["p_value_two_sided"] == 1
    assert result["significant"] is False


def test_large_difference_significant():
    result = analyze_binary_experiment(
        control_conversions=100, control_total=1000,
        treatment_conversions=200, treatment_total=1000,
    )
    assert isclose(result["absolute_lift"], 0.1)
    assert result["p_value_two_sided"] < 0.001
    assert result["significant"] is True
    assert result["difference_ci_wald"]["lower"] > 0


def test_zero_baseline_relative_lift_undefined():
    result = analyze_binary_experiment(
        control_conversions=0, control_total=100,
        treatment_conversions=10, treatment_total=100,
    )
    assert result["relative_lift"] is None


def test_all_zero_or_all_one_not_significant():
    for successes in (0, 20):
        result = analyze_binary_experiment(
            control_conversions=successes, control_total=20,
            treatment_conversions=successes, treatment_total=20,
        )
        assert result["p_value_two_sided"] == 1
        assert result["significant"] is False


@pytest.mark.parametrize("kwargs", [
    {"control_conversions": -1, "control_total": 10, "treatment_conversions": 1, "treatment_total": 10},
    {"control_conversions": 11, "control_total": 10, "treatment_conversions": 1, "treatment_total": 10},
    {"control_conversions": 1, "control_total": 0, "treatment_conversions": 1, "treatment_total": 10},
    {"control_conversions": 1, "control_total": 10, "treatment_conversions": 1, "treatment_total": 10, "alpha": 0},
    {"control_conversions": 1, "control_total": 10, "treatment_conversions": 1, "treatment_total": 10, "alpha": float("nan")},
])
def test_invalid_experiments(kwargs):
    with pytest.raises(ValueError):
        analyze_binary_experiment(**kwargs)


def test_boolean_counts_rejected():
    with pytest.raises(TypeError):
        analyze_binary_experiment(
            control_conversions=True, control_total=10,
            treatment_conversions=1, treatment_total=10,
        )
