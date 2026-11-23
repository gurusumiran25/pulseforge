"""Versioned, privacy-minimal synthetic payment sidecar for dashboard analytics.

The sidecar is opt-in and not yet published by the scheduled workflow.
"""
import csv
import hashlib
import json
from pathlib import Path

from services.storage.sqlite_store import SQLiteEventStore


FIELDS = ("event_id", "event_name", "user_id", "event_time", "order_id", "amount", "currency")


def export_payment_sidecar(db_path, output_path):
    """Export synthetic payment events without full event payloads.

    Refunds use the amount column for refund_amount. The consumer must
    interpret amount based on event_name. CSV schema version is 1.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with SQLiteEventStore(db_path).connect() as connection:
        rows = connection.execute(
            "SELECT payload FROM events WHERE event_name IN "
            "('payment_succeeded', 'order_refunded') ORDER BY event_time, event_id"
        ).fetchall()
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            event = json.loads(row["payload"])
            props = event["properties"]
            name = event["event_name"]
            writer.writerow({
                "event_id": event["event_id"],
                "event_name": name,
                "user_id": event["user_id"],
                "event_time": event["event_time"],
                "order_id": props["order_id"],
                "amount": props["amount"] if name == "payment_succeeded" else props["refund_amount"],
                "currency": props["currency"],
            })
            count += 1
    return {"schema_version": 1, "rows": count, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def load_payment_sidecar(path, *, expected_sha256, expected_rows):
    """Verify hash, row count and strict schema before analytics consumption."""
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Payment sidecar SHA-256 mismatch")
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("Payment sidecar schema mismatch")
        rows = list(reader)
    if len(rows) != expected_rows:
        raise ValueError("Payment sidecar row count mismatch")
    seen = set()
    result = []
    for row in rows:
        if not all(row.get(field) for field in FIELDS):
            raise ValueError("Missing payment sidecar field")
        if row["event_id"] in seen:
            raise ValueError("Duplicate payment sidecar event_id")
        seen.add(row["event_id"])
        name = row["event_name"]
        if name not in ("payment_succeeded", "order_refunded"):
            raise ValueError("Unsupported payment sidecar event")
        props = {"order_id": row["order_id"], "currency": row["currency"]}
        props["amount" if name == "payment_succeeded" else "refund_amount"] = row["amount"]
        result.append({
            "event_name": name,
            "user_id": row["user_id"],
            "event_time": row["event_time"],
            "properties": props,
        })
    return result
