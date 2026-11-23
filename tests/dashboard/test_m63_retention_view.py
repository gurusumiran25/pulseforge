"""M63 retention right-censoring regression tests."""
from datetime import date

import pytest

from apps.dashboard.retention_view import mask_immature_retention


def test_immature_horizons_blank_but_mature_zero_preserved():
    rows = [{"cohort_date_utc": "2026-11-20", "users": 5,
             "day_1_users": 0, "day_1_retention_pct": 0.0,
             "day_7_users": 0, "day_7_retention_pct": 0.0}]
    result = mask_immature_retention(rows, observation_end_date=date(2026, 11, 23))
    assert result[0]["day_1_users"] == 0
    assert result[0]["day_1_retention_pct"] == 0.0
    assert result[0]["day_7_users"] is None
    assert result[0]["day_7_retention_pct"] is None
    assert rows[0]["day_7_users"] == 0


def test_exact_boundary_is_mature():
    rows = [{"cohort_date_utc": "2026-11-16", "day_7_users": 2,
             "day_7_retention_pct": 20.0}]
    assert mask_immature_retention(rows, observation_end_date=date(2026, 11, 23))[0]["day_7_users"] == 2


def test_cohort_after_observation_end_rejected():
    with pytest.raises(ValueError):
        mask_immature_retention([{"cohort_date_utc": "2026-11-24"}],
                                observation_end_date=date(2026, 11, 23))
