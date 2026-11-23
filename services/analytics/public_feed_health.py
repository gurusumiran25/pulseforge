"""Fail closed when the published synthetic dashboard feed is stale or corrupted."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.analytics.bronze_manifest import verify_manifest
from services.analytics.payment_sidecar import load_payment_sidecar


def verify_published_feed(directory, *, now=None, max_age_hours=36, require_payment_sidecar=False):
    if max_age_hours <= 0:
        raise ValueError("max_age_hours must be positive")
    directory = Path(directory)
    status = json.loads((directory / "status.json").read_text(encoding="utf-8"))
    manifest_path = directory / "latest_bronze.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = manifest.get("generated_at_utc")
    if not isinstance(raw, str):
        raise TypeError("Missing publication timestamp")
    try:
        published = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid publication timestamp") from exc
    if published.tzinfo is None or published.utcoffset() is None:
        raise ValueError("Publication timestamp requires timezone")
    current = now or datetime.now(timezone.utc)
    if published > current + timedelta(minutes=10):
        raise ValueError("Publication timestamp is in the future")
    age = current - published
    if age > timedelta(hours=max_age_hours):
        raise ValueError(f"Published feed is stale ({age.total_seconds() / 3600:.1f} hours)")
    if status.get("status") != "passed" or status.get("quality_checks") != 8:
        raise ValueError("Published feed quality status is not passed")
    if status.get("as_of_utc") != published.date().isoformat():
        raise ValueError("Publication date disagrees with status")
    stats = verify_manifest(directory / "latest_bronze.csv", manifest_path)
    if stats["rows"] != status.get("events"):
        raise ValueError("Published event count disagrees with status")
    payment_metadata = status.get("payment_sidecar")
    if require_payment_sidecar and not isinstance(payment_metadata, dict):
        raise ValueError("Required payment sidecar is missing")
    payment_count = None
    if payment_metadata is not None:
        if not isinstance(payment_metadata, dict) or payment_metadata.get("schema_version") != 1:
            raise ValueError("Unsupported payment sidecar metadata")
        if payment_metadata.get("bronze_sha256") != stats["sha256"]:
            raise ValueError("Payment sidecar is not linked to published Bronze snapshot")
        payment_rows = load_payment_sidecar(
            directory / "latest_payments.csv",
            expected_sha256=payment_metadata["sha256"],
            expected_rows=payment_metadata["rows"],
        )
        payment_count = len(payment_rows)
        paid = sum(row["event_name"] == "payment_succeeded" for row in payment_rows)
        if paid != status.get("paid_sessions"):
            raise ValueError("Payment sidecar successful-payment count disagrees with status")
    return {"healthy": True, "events": stats["rows"], "age_hours": round(age.total_seconds() / 3600, 2),
            "payment_rows": payment_count}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default="data/public")
    parser.add_argument("--max-age-hours", type=float, default=36)
    parser.add_argument("--require-payment-sidecar", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify_published_feed(args.directory, max_age_hours=args.max_age_hours,
                                          require_payment_sidecar=args.require_payment_sidecar)))


if __name__ == "__main__":
    main()
