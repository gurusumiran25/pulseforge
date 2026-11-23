"""Presentation-only right-censoring for observed UTC retention cohorts."""
from datetime import date, timedelta


def mask_immature_retention(cohorts, *, observation_end_date, horizons=(1, 7, 14, 30)):
    """Mark unobservable follow-up windows as None, not zero retention.

    A cohort needs its complete follow-up day in the observed data window.
    No changes are made to the underlying event-level retention calculation.
    """
    if not isinstance(observation_end_date, date):
        raise TypeError("observation_end_date must be a date")
    result = []
    for cohort in cohorts:
        cohort_date = date.fromisoformat(cohort["cohort_date_utc"])
        if cohort_date > observation_end_date:
            raise ValueError("Cohort cannot start after observation window")
        row = dict(cohort)
        for horizon in horizons:
            if cohort_date + timedelta(days=horizon) > observation_end_date:
                row[f"day_{horizon}_users"] = None
                row[f"day_{horizon}_retention_pct"] = None
        result.append(row)
    return result
