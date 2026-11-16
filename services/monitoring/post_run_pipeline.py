"""M18 post-simulation monitoring pipeline.

Stage 5 is preview-only and does not execute simulation.
"""

import argparse
import json

from services.monitoring.metrics_collector import collect_metrics
from services.monitoring.snapshot_store import build_snapshot
from services.monitoring.quality_refresh import refresh_quality


def run_post_simulation(preview=True):
    if preview is not True:
        raise ValueError("Execution is disabled in M18 Stage 5")

    quality = refresh_quality(execute=False)
    metrics = collect_metrics()
    snapshot = build_snapshot(metrics)

    return {
        "mode": "PREVIEW",
        "simulation_executed": False,
        "quality_report_persisted": False,
        "snapshot_persisted": False,
        "quality_preview": quality,
        "monitoring": {
            "overall_status": snapshot["overall_status"],
            "assessment_scope": snapshot["assessment_scope"],
            "event_count": metrics["storage"]["events"]["row_count"],
            "customer_count": metrics["storage"]["customers"]["row_count"],
            "alert_count": len(snapshot["alerts"]),
            "alert_codes": [
                alert["code"] for alert in snapshot["alerts"]
            ],
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    if not args.preview:
        parser.error("Stage 5 requires --preview")

    result = run_post_simulation(preview=True)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
