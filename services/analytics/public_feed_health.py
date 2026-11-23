"""Fail closed when the published synthetic dashboard feed is stale or corrupted."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.analytics.bronze_manifest import verify_manifest


def verify_published_feed(directory, *, now=None, max_age_hours=36):
    if max_age_hours <= 0:
        raise ValueError("max_age_hours must be positive")
    directory = Path(directory)
    status = json.loads((directory / "status.json").read_text(encoding="utf-8"))
    manifest_path = directory / "latest_bronze.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = manifest.get("generated_at_utc")
    if not isinstance(raw, str):
        raise ValueError("Missing publication timestamp")
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
    return {"healthy": True, "events": stats["rows"], "age_hours": round(age.total_seconds() / 3600, 2)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default="data/public")
    parser.add_argument("--max-age-hours", type=float, default=36)
    args = parser.parse_args()
    print(json.dumps(verify_published_feed(args.directory, max_age_hours=args.max_age_hours)))


if __name__ == "__main__":
    main()
