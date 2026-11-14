"""Deterministic operational alert evaluation for PulseForge."""

import hashlib
import json

from services.monitoring.metrics_collector import collect_metrics
from services.monitoring.quality_monitor import evaluate_quality


def _make_alert(code, severity, component, message):
    identity = f"{component}:{code}"

    alert_id = hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()[:16]

    return {
        "alert_id": alert_id,
        "code": code,
        "severity": severity,
        "component": component,
        "message": message,
    }


def evaluate_alerts(metrics):
    alerts = []

    storage = metrics.get("storage", {})

    for database in ("events", "customers"):
        integrity = storage.get(database, {}).get("integrity")

        if integrity is not None and integrity != "ok":
            alerts.append(_make_alert(
                f"{database.upper()}_DB_INTEGRITY_FAILURE",
                "CRITICAL",
                "storage",
                f"{database} database integrity check failed",
            ))

        elif integrity is None:
            alerts.append(_make_alert(
                f"{database.upper()}_DB_INTEGRITY_UNKNOWN",
                "WARNING",
                "storage",
                f"{database} database integrity was not verified",
            ))

    quality = metrics.get("data_quality", {})

    if quality.get("status") == "UNKNOWN":
        alerts.append(_make_alert(
            "QUALITY_REPORT_MISSING",
            "WARNING",
            "data_quality",
            "Quality report is unavailable or unverified",
        ))

    elif quality.get("coverage_current") is False:
        alerts.append(_make_alert(
            "QUALITY_REPORT_OUTDATED",
            "WARNING",
            "data_quality",
            "Quality report does not cover current event data",
        ))

    assessment = evaluate_quality(metrics)

    if assessment["status"] == "CRITICAL":
        alerts.append(_make_alert(
            "QUALITY_CRITICAL",
            "CRITICAL",
            "data_quality",
            "; ".join(assessment["reasons"]),
        ))

    elif assessment["status"] == "DEGRADED":
        if quality.get("coverage_current") is not False:
            alerts.append(_make_alert(
                "QUALITY_DEGRADED",
                "WARNING",
                "data_quality",
                "; ".join(assessment["reasons"]),
            ))

    elif assessment["status"] == "UNKNOWN":
        if quality.get("status") != "UNKNOWN":
            alerts.append(_make_alert(
                "QUALITY_EVIDENCE_UNKNOWN",
                "WARNING",
                "data_quality",
                "; ".join(assessment["reasons"]),
            ))

    return sorted(
        alerts,
        key=lambda alert: (
            0 if alert["severity"] == "CRITICAL" else 1,
            alert["component"],
            alert["code"],
        ),
    )


if __name__ == "__main__":
    metrics = collect_metrics()
    alerts = evaluate_alerts(metrics)

    print(json.dumps({
        "total_alerts": len(alerts),
        "alerts": alerts,
    }, indent=2))
