"""Combined, read-only PulseForge data quality reporting."""

import json
from datetime import datetime, timezone
from pathlib import Path

from services.quality.event_scanner import scan_events
from services.quality.integrity import audit_integrity
from services.quality.scoring import score_quality
from services.quality.volume_anomaly import detect_volume_anomalies


def generate_report(event_db, customer_db):
    scan = scan_events(event_db, customer_db)
    integrity = audit_integrity(event_db, customer_db)
    volume = detect_volume_anomalies(event_db)

    issues = scan["issues"] + integrity["issues"]

    for anomaly in volume["anomalies"]:
        issues.append({
            "event_id": None,
            "issue": "EVENT_VOLUME_ANOMALY",
            "date": anomaly["date"],
            "direction": anomaly["direction"],
            "observed_events": anomaly["observed_events"],
            "baseline_average": anomaly["baseline_average"],
            "deviation_percent": anomaly["deviation_percent"],
        })
    scoring = score_quality(issues, scan["total_events"])

    return {
        "report_type": "PULSEFORGE_DATA_QUALITY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not issues else "REVIEW",
        "total_events": scan["total_events"],
        "total_issues": len(issues),
        "quality_score": scoring["quality_score"],
        "quality_grade": scoring["grade"],
        "severity_counts": scoring["severity_counts"],
        "integrity_metrics": integrity["metrics"],
        "volume_anomaly_metrics": volume,
        "checks": {
            "event_schema_and_references": "COMPLETED",
            "database_integrity": "COMPLETED",
            "duplicate_activity": "COMPLETED",
            "session_consistency": "COMPLETED",
            "volume_anomaly_detection": volume["status"],
        },
        "issues": scoring["classified_issues"],
    }


if __name__ == "__main__":
    report = generate_report(
        "data/automation/events.db",
        "data/automation/customers.db",
    )

    directory = Path("reports/quality")
    directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = directory / f"quality_{timestamp}.json"

    with destination.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print(json.dumps({
        "report_path": str(destination),
        "status": report["status"],
        "total_events": report["total_events"],
        "total_issues": report["total_issues"],
        "quality_score": report["quality_score"],
        "quality_grade": report["quality_grade"],
        "checks": report["checks"],
    }, indent=2))
