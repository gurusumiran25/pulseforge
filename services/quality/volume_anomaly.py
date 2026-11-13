"""Read-only daily event volume anomaly detection."""

import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo


def detect_volume_anomalies(
    event_db,
    min_baseline_days=7,
    deviation_threshold=0.50,
    timezone_name="Asia/Kolkata",
    as_of_date=None,
):
    if min_baseline_days < 1:
        raise ValueError("min_baseline_days must be positive")
    if not 0 < deviation_threshold < 1:
        raise ValueError("deviation_threshold must be between 0 and 1")

    path = Path(event_db)
    if not path.is_file():
        raise FileNotFoundError(path)

    timezone = ZoneInfo(timezone_name)
    uri = path.resolve().as_uri() + "?mode=ro"
    daily = Counter()

    with sqlite3.connect(uri, uri=True) as conn:
        for (value,) in conn.execute("SELECT event_time FROM events"):
            timestamp = datetime.fromisoformat(value)
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError("Event timestamp lacks timezone")
            day = timestamp.astimezone(timezone).date()
            daily[day] += 1

    # Exclude the current/incomplete day from baseline and evaluation.
    cutoff = (
        datetime.now(timezone).date()
        if as_of_date is None
        else as_of_date
    )

    complete_days = {
        day: count for day, count in daily.items() if day < cutoff
    }

    if not complete_days:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "complete_days": 0,
            "anomalies": [],
        }

    first_day = min(complete_days)
    last_day = max(complete_days)

    # Include zero-event days within the observed calendar range.
    dates = [
        first_day + timedelta(days=i)
        for i in range((last_day - first_day).days + 1)
    ]

    anomalies = []
    evaluated_days = 0

    for index in range(min_baseline_days, len(dates)):
        day = dates[index]
        baseline = [
            complete_days.get(previous, 0)
            for previous in dates[index - min_baseline_days:index]
        ]

        baseline_average = mean(baseline)
        observed = complete_days.get(day, 0)
        evaluated_days += 1

        if baseline_average == 0:
            continue

        deviation = (observed - baseline_average) / baseline_average

        if abs(deviation) >= deviation_threshold:
            anomalies.append({
                "date": day.isoformat(),
                "observed_events": observed,
                "baseline_average": round(baseline_average, 2),
                "deviation_percent": round(deviation * 100, 2),
                "direction": "SPIKE" if deviation > 0 else "DROP",
            })

    return {
        "status": (
            "INSUFFICIENT_HISTORY"
            if evaluated_days == 0
            else "ANOMALIES_DETECTED" if anomalies else "PASS"
        ),
        "complete_days": len(dates),
        "evaluated_days": evaluated_days,
        "baseline_days": min_baseline_days,
        "anomalies": anomalies,
    }
