"""M62: repeated synthetic identities make daily retention measurable."""
from datetime import date

import pytest

from services.analytics.daily_public_feed import synthetic_user_id


def test_returning_id_stable_across_days():
    first = synthetic_user_id(date(2026, 11, 1), 3)
    second = synthetic_user_id(date(2026, 11, 2), 3)
    assert first == second
    assert first.startswith("synthetic_returning_")


def test_new_users_are_unique_by_date_and_index():
    first = synthetic_user_id(date(2026, 11, 1), 20)
    second = synthetic_user_id(date(2026, 11, 2), 20)
    assert first != second
    assert synthetic_user_id(date(2026, 11, 1), 21) != first


def test_identity_groups_do_not_overlap():
    ids = {synthetic_user_id(date(2026, 11, day), index)
           for day in (1, 2) for index in range(40)}
    assert len(ids) == 70  # 10 returning + 30 new each day


@pytest.mark.parametrize("index,repeat_users", [(-1, 10), (0, -1)])
def test_negative_values_rejected(index, repeat_users):
    with pytest.raises(ValueError):
        synthetic_user_id(date(2026, 11, 1), index, repeat_users=repeat_users)
