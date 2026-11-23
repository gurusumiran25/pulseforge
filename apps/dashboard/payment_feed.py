"""Load synthetic payment sidecar only when tied to a verified Bronze snapshot."""
import hashlib
import json
import tempfile
from pathlib import Path

from apps.dashboard.public_feed import (
    MAX_MANIFEST_BYTES,
    _download,
    validate_publication_timestamp,
)
from services.analytics.payment_sidecar import load_payment_sidecar

MAX_PAYMENT_BYTES = 4_000_000


def load_verified_payment_feed(bronze_manifest):
    """Fail closed on mismatched GitHub raw-cache snapshots or missing sidecar."""
    status = json.loads(_download("status.json", MAX_MANIFEST_BYTES))
    metadata = status.get("payment_sidecar")
    if not isinstance(metadata, dict) or metadata.get("schema_version") != 1:
        raise ValueError("Payment feed not yet published or unsupported")
    if metadata.get("bronze_sha256") != bronze_manifest.get("sha256"):
        raise ValueError("Payment/Bronze snapshots differ; retry after cache propagation")
    validate_publication_timestamp(bronze_manifest)
    digest = metadata.get("sha256")
    count = metadata.get("rows")
    if not isinstance(digest, str) or len(digest) != 64 or not isinstance(count, int) or count < 0:
        raise ValueError("Invalid payment feed metadata")
    raw = _download("latest_payments.csv", MAX_PAYMENT_BYTES)
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Payment feed digest mismatch")
    with tempfile.TemporaryDirectory(prefix="pulseforge-payment-feed-") as temp:
        path = Path(temp) / "payments.csv"
        path.write_bytes(raw)
        return load_payment_sidecar(path, expected_sha256=digest, expected_rows=count)
