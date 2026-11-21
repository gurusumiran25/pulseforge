"""Integrity manifest for an immutable-at-rest Bronze CSV snapshot.

This is a verifiable sidecar, not an atomic two-file transaction or a lock.
"""
import argparse
import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from services.analytics.bronze_export import FIELDS


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_bronze(path):
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("Invalid Bronze CSV schema")
        ids = set()
        count = 0
        for row in reader:
            if not all(row.get(field) for field in FIELDS):
                raise ValueError("Blank required Bronze field")
            if row["event_id"] in ids:
                raise ValueError("Duplicate event_id in Bronze CSV")
            ids.add(row["event_id"])
            count += 1
    return {"rows": count, "sha256": _sha256(path)}


def write_manifest(csv_path, manifest_path):
    csv_path = Path(csv_path)
    manifest_path = Path(manifest_path)
    if csv_path.resolve() == manifest_path.resolve():
        raise ValueError("Manifest cannot overwrite Bronze CSV")
    stats = inspect_bronze(csv_path)
    manifest = {
        "schema_version": 1,
        "rows": stats["rows"],
        "sha256": stats["sha256"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=manifest_path.parent,
            prefix=".bronze-manifest-", suffix=".json", delete=False,
        ) as handle:
            temporary = handle.name
            json.dump(manifest, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        # Fail if a writer replaced the CSV while the manifest was being written.
        if inspect_bronze(csv_path) != stats:
            raise RuntimeError("Bronze CSV changed while preparing manifest")
        os.replace(temporary, manifest_path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return manifest


def verify_manifest(csv_path, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported Bronze manifest version")
    stats = inspect_bronze(csv_path)
    if manifest.get("rows") != stats["rows"] or manifest.get("sha256") != stats["sha256"]:
        raise ValueError("Bronze CSV does not match checkpoint manifest")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Create or verify a Bronze integrity manifest")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        print(verify_manifest(args.csv, args.manifest))
    else:
        print(write_manifest(args.csv, args.manifest))


if __name__ == "__main__":
    main()
