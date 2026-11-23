"""Bounded retry for transient CDN snapshot inconsistencies.

Each attempt re-downloads and re-verifies the feed. Integrity checks are never bypassed.
"""
import time


def retry_verified_feed(loader, *, attempts=3, delay_seconds=0.5, sleep=time.sleep):
    if attempts < 1 or delay_seconds < 0:
        raise ValueError("Invalid retry configuration")
    for attempt in range(attempts):
        try:
            return loader()
        except (OSError, ValueError, TypeError, KeyError):
            if attempt + 1 >= attempts:
                raise
            sleep(delay_seconds)
