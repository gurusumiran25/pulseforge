"""Independent remote CDN smoke for the publicly hosted synthetic dashboard feed.

Downloads the same GitHub raw artifacts as Streamlit; no live browser claim.
"""
import argparse
import json
import time
from datetime import datetime, timezone

from apps.dashboard.payment_feed import load_verified_payment_feed
from apps.dashboard.public_feed import MAX_MANIFEST_BYTES, _download, load_verified_public_feed


def verify_remote_publication(*, max_age_hours=36):
    events, manifest = load_verified_public_feed()
    payments = load_verified_payment_feed(manifest)
    status = json.loads(_download("status.json", MAX_MANIFEST_BYTES))
    published = datetime.fromisoformat(
        manifest["generated_at_utc"].replace("Z", "+00:00")
    )
    age_hours = (datetime.now(timezone.utc) - published).total_seconds() / 3600
    if age_hours > max_age_hours:
        raise ValueError(f"Remote publication stale: {age_hours:.2f} hours")
    paid = sum(event["event_name"] == "payment_succeeded" for event in payments)
    if not events or not payments or not paid:
        raise ValueError("Remote feed unexpectedly empty")
    if status.get("status") != "passed" or status.get("quality_checks") != 8:
        raise ValueError("Remote publication quality status failed")
    if status.get("events") != len(events) or status.get("paid_sessions") != paid:
        raise ValueError("Remote publication status counts disagree with verified feed")
    if status.get("as_of_utc") != published.date().isoformat():
        raise ValueError("Remote publication date disagrees with manifest")
    metadata = status.get("payment_sidecar", {})
    if metadata.get("rows") != len(payments) or metadata.get("bronze_sha256") != manifest.get("sha256"):
        raise ValueError("Remote payment status disagrees with verified feed")
    return {
        "healthy": True,
        "generated_at_utc": manifest["generated_at_utc"],
        "bronze_sha256": manifest["sha256"],
        "events": len(events),
        "payment_rows": len(payments),
        "successful_payments": paid,
        "age_hours": round(age_hours, 2),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-age-hours", type=float, default=36)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--retry-seconds", type=float, default=15)
    args = parser.parse_args()
    if args.attempts < 1 or args.retry_seconds < 0 or args.max_age_hours <= 0:
        parser.error("attempts and max-age-hours must be positive; retry-seconds nonnegative")
    for attempt in range(args.attempts):
        try:
            print(json.dumps(verify_remote_publication(max_age_hours=args.max_age_hours)))
            return
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            if attempt + 1 == args.attempts:
                raise
            print(f"Remote snapshot not yet consistent ({type(exc).__name__}); retrying", flush=True)
            time.sleep(args.retry_seconds)


if __name__ == "__main__":
    main()
