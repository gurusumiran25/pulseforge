"""Read the public GitHub-hosted feed with a verified integrity manifest."""
import hashlib
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from apps.dashboard.metrics import load_events

BASE_URL = "https://raw.githubusercontent.com/gurusumiran25/pulseforge/main/data/public/"
MAX_CSV_BYTES = 4_000_000
MAX_MANIFEST_BYTES = 16_384


def _download(name, limit):
    request = Request(BASE_URL + name, headers={"Cache-Control": "no-cache", "User-Agent": "PulseForgeDashboard/1.0"})
    with urlopen(request, timeout=12) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Public dataset exceeds size limit")
    return data


def validate_publication_timestamp(manifest, *, now=None):
    """Reject absent, naive, invalid, or implausibly future-dated feed timestamps."""
    raw = manifest.get("generated_at_utc")
    if not isinstance(raw, str):
        raise TypeError("Missing public feed publication timestamp")
    try:
        published = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid public feed publication timestamp") from exc
    if published.tzinfo is None or published.utcoffset() is None:
        raise ValueError("Public feed publication timestamp must include timezone")
    current = now or datetime.now(timezone.utc)
    if published > current + timedelta(minutes=10):
        raise ValueError("Public feed publication timestamp is in the future")
    return published.astimezone(timezone.utc)


def load_verified_public_feed():
    manifest = json.loads(_download("latest_bronze.manifest.json", MAX_MANIFEST_BYTES))
    csv_bytes = _download("latest_bronze.csv", MAX_CSV_BYTES)
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported public feed manifest")
    validate_publication_timestamp(manifest)
    if hashlib.sha256(csv_bytes).hexdigest() != manifest.get("sha256"):
        raise ValueError("Public feed integrity mismatch; retry after GitHub cache propagation")
    # Reuse existing strict event validation rather than introducing a second parser.
    with tempfile.TemporaryDirectory(prefix="pulseforge-public-feed-") as temp:
        path = Path(temp) / "feed.csv"
        path.write_bytes(csv_bytes)
        events = load_events(path)
    if len(events) != manifest.get("rows"):
        raise ValueError("Public feed row count mismatch")
    return events, manifest
