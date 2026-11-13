"""End-to-end orchestration tests for quality reporting."""

from unittest.mock import patch

from services.quality.report import generate_report


def clean_scan():
    return {
        "total_events": 3025,
        "total_issues": 0,
        "events_with_issues": 0,
        "status": "PASS",
        "issues": [],
    }


def clean_integrity():
    return {
        "status": "PASS",
        "metrics": {"sqlite_integrity": "ok"},
        "issues": [],
    }


def volume_result(status, anomalies=None):
    return {
        "status": status,
        "complete_days": 9,
        "evaluated_days": 2,
        "baseline_days": 7,
        "anomalies": anomalies or [],
    }


def run_report(volume):
    with (
        patch(
            "services.quality.report.scan_events",
            return_value=clean_scan(),
        ),
        patch(
            "services.quality.report.audit_integrity",
            return_value=clean_integrity(),
        ),
        patch(
            "services.quality.report.detect_volume_anomalies",
            return_value=volume,
        ),
    ):
        return generate_report("unused_events.db", "unused_customers.db")


def test_clean_report():
    result = run_report(volume_result("PASS"))

    assert result["status"] == "PASS"
    assert result["total_issues"] == 0
    assert result["quality_score"] == 100.0


def test_insufficient_history_is_not_a_failure():
    result = run_report(volume_result("INSUFFICIENT_HISTORY"))

    assert result["status"] == "PASS"
    assert result["total_issues"] == 0
    assert result["checks"]["volume_anomaly_detection"] == (
        "INSUFFICIENT_HISTORY"
    )


def test_volume_drop_creates_report_issue():
    anomaly = {
        "date": "2026-10-08",
        "observed_events": 20,
        "baseline_average": 100.0,
        "deviation_percent": -80.0,
        "direction": "DROP",
    }

    result = run_report(
        volume_result("ANOMALIES_DETECTED", [anomaly])
    )

    assert result["status"] == "REVIEW"
    assert result["total_issues"] == 1
    assert result["issues"][0]["issue"] == "EVENT_VOLUME_ANOMALY"
    assert result["issues"][0]["direction"] == "DROP"
    assert result["issues"][0]["severity"] == "MEDIUM"
    assert result["quality_score"] < 100.0


def test_volume_spike_creates_report_issue():
    anomaly = {
        "date": "2026-10-09",
        "observed_events": 200,
        "baseline_average": 88.57,
        "deviation_percent": 125.81,
        "direction": "SPIKE",
    }

    result = run_report(
        volume_result("ANOMALIES_DETECTED", [anomaly])
    )

    assert result["status"] == "REVIEW"
    assert result["total_issues"] == 1
    assert result["issues"][0]["direction"] == "SPIKE"


def test_multiple_anomalies_counted():
    anomalies = [
        {
            "date": "2026-10-08",
            "observed_events": 20,
            "baseline_average": 100.0,
            "deviation_percent": -80.0,
            "direction": "DROP",
        },
        {
            "date": "2026-10-09",
            "observed_events": 200,
            "baseline_average": 88.57,
            "deviation_percent": 125.81,
            "direction": "SPIKE",
        },
    ]

    result = run_report(
        volume_result("ANOMALIES_DETECTED", anomalies)
    )

    assert result["status"] == "REVIEW"
    assert result["total_issues"] == 2
    assert result["severity_counts"]["MEDIUM"] == 2
