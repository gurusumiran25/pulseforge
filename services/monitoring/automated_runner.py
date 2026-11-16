"""M18 automated monitoring orchestration foundation.

Stage 3 supports read-only preview only.
"""

import argparse
import json

from services.monitoring.metrics_collector import collect_metrics
from services.monitoring.snapshot_store import build_snapshot


def run_monitoring(preview=True):
    if preview is not True:
        raise ValueError(
            "Persistence is disabled until M18 safety controls are implemented"
        )

    metrics = collect_metrics()
    snapshot = build_snapshot(metrics)

    return {
        "mode": "PREVIEW",
        "persisted": False,
        "generated_at_utc": snapshot["generated_at_utc"],
        "overall_status": snapshot["overall_status"],
        "assessment_scope": snapshot["assessment_scope"],
        "event_count": metrics["storage"]["events"]["row_count"],
        "customer_count": metrics["storage"]["customers"]["row_count"],
        "quality_status": snapshot["quality_assessment"]["status"],
        "alert_count": len(snapshot["alerts"]),
        "alert_codes": [
            alert["code"] for alert in snapshot["alerts"]
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="PulseForge automated monitoring runner"
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Run monitoring without writing any data",
    )

    args = parser.parse_args()

    if not args.preview:
        parser.error(
            "Only --preview is supported during M18 Stage 3"
        )

    result = run_monitoring(preview=True)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
