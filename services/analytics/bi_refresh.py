"""Verify a pinned BI snapshot before handing its ID to a refresh consumer."""
import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from services.analytics.bi_model import validate_model


def verify_refresh(root, now=None, max_age_hours=48):
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or max_age_hours <= 0:
        raise ValueError("Invalid freshness policy")
    pointer = json.loads((root / "current.json").read_bytes())
    snapshot = pointer["snapshot"]
    if pointer["schema_version"] != 1 or not re.fullmatch(r"[0-9a-f]{64}", snapshot):
        raise ValueError("Invalid snapshot pointer")
    folder = root / snapshot
    raw = (folder / "manifest.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != snapshot:
        raise ValueError("Manifest integrity failure")
    manifest = json.loads(raw)
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported manifest")
    tables = {}
    for name, metadata in manifest["files"].items():
        if Path(name).name != name or "\\" in name or not name.endswith(".csv"):
            raise ValueError("Invalid file name")
        data = (folder / name).read_bytes()
        if len(data) != metadata["bytes"] or hashlib.sha256(data).hexdigest() != metadata["sha256"]:
            raise ValueError("File integrity failure")
        tables[name] = data
    counts = validate_model(tables)
    events = csv.DictReader(io.StringIO(tables["FactEvent.csv"].decode()))
    latest = max((datetime.fromisoformat(r["event_time_utc"].replace("Z", "+00:00")) for r in events), default=None)
    if latest is None or latest.tzinfo is None or latest > now or now - latest > timedelta(hours=max_age_hours):
        raise ValueError("Stale, empty or future-dated snapshot")
    return {"snapshot": snapshot, "latest_event_utc": latest.isoformat(), "counts": counts}
