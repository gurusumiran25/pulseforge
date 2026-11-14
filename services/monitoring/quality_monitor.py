"""Evaluate PulseForge data-quality monitoring health."""

import json

from services.monitoring.metrics_collector import collect_metrics


def evaluate_quality(metrics, warning_hours=24, critical_hours=48):
    if warning_hours <= 0 or critical_hours <= warning_hours:
        raise ValueError("Invalid freshness thresholds")

    quality = metrics.get("data_quality", {})
    storage = metrics.get("storage", {})

    reasons = []

    for name in ("events", "customers"):
        database = storage.get(name, {})

        if database.get("integrity") != "ok":
            return {
                "status": "CRITICAL",
                "reasons": [f"{name} database integrity not verified"],
            }

    if quality.get("status") == "UNKNOWN":
        return {
            "status": "UNKNOWN",
            "reasons": [quality.get("reason", "Quality evidence unavailable")],
        }

    required = (
        "status",
        "score",
        "grade",
        "report_age_hours",
        "coverage_current",
    )

    if any(quality.get(key) is None for key in required):
        return {
            "status": "UNKNOWN",
            "reasons": ["Incomplete quality report metrics"],
        }

    try:
        score = float(quality["score"])
        age = float(quality["report_age_hours"])
    except (TypeError, ValueError, OverflowError):
        return {
            "status": "UNKNOWN",
            "reasons": ["Invalid quality score or report age"],
        }

    if not (0 <= score <= 100) or not (0 <= age < float("inf")):
        return {
            "status": "UNKNOWN",
            "reasons": ["Quality score or report age outside valid range"],
        }

    if quality["coverage_current"] is not True:
        reasons.append("Quality report does not cover current event count")

    if age >= critical_hours:
        reasons.append("Quality report exceeds critical freshness threshold")
    elif age >= warning_hours:
        reasons.append("Quality report exceeds warning freshness threshold")

    if quality["grade"] == "CRITICAL" or score < 70:
        return {
            "status": "CRITICAL",
            "reasons": reasons + ["Critical quality grade or score"],
        }

    if quality["status"] not in ("PASS", "REVIEW"):
        return {
            "status": "UNKNOWN",
            "reasons": reasons + ["Unrecognized quality report status"],
        }

    if quality["grade"] not in ("EXCELLENT", "GOOD", "WARNING"):
        return {
            "status": "UNKNOWN",
            "reasons": reasons + ["Unrecognized quality grade"],
        }

    if quality["status"] == "REVIEW":
        reasons.append("Quality report requires review")

    if score < 95:
        reasons.append("Quality score below warning threshold")

    if reasons:
        return {
            "status": "DEGRADED",
            "reasons": reasons,
        }

    return {
        "status": "HEALTHY",
        "reasons": [],
    }


if __name__ == "__main__":
    metrics = collect_metrics()
    assessment = evaluate_quality(metrics)

    print(json.dumps({
        "component": "data_quality",
        "assessment": assessment,
        "report_status": metrics["data_quality"].get("status"),
        "report_score": metrics["data_quality"].get("score"),
        "coverage_current": metrics["data_quality"].get("coverage_current"),
    }, indent=2))
