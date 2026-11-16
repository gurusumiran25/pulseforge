"""Deterministic failure classification for PulseForge M18."""

import sqlite3


def classify_failure(error=None, alert_code=None):
    """Classify an exception or monitoring alert.

    Classification does not authorize automatic recovery.
    """

    if error is not None and alert_code is not None:
        raise ValueError(
            "Provide either error or alert_code, not both"
        )

    if error is None and alert_code is None:
        raise ValueError(
            "An error or alert_code is required"
        )

    if alert_code is not None:
        if not isinstance(alert_code, str):
            raise TypeError("alert_code must be a string")

        if alert_code in (
            "QUALITY_REPORT_MISSING",
            "QUALITY_REPORT_OUTDATED",
        ):
            return {
                "category": "RECOVERABLE",
                "code": alert_code,
                "retry_eligible": False,
                "suggested_action": "REFRESH_QUALITY_REPORT",
            }

        if alert_code in (
            "EVENTS_DB_INTEGRITY_FAILURE",
            "CUSTOMERS_DB_INTEGRITY_FAILURE",
            "QUALITY_CRITICAL",
        ):
            return {
                "category": "CRITICAL",
                "code": alert_code,
                "retry_eligible": False,
                "suggested_action": "MANUAL_INVESTIGATION",
            }

        return {
            "category": "UNKNOWN",
            "code": alert_code,
            "retry_eligible": False,
            "suggested_action": "MANUAL_INVESTIGATION",
        }

    if isinstance(error, FileNotFoundError):
        return {
            "category": "CRITICAL",
            "code": "SOURCE_FILE_MISSING",
            "retry_eligible": False,
            "suggested_action": "MANUAL_INVESTIGATION",
        }

    if isinstance(error, sqlite3.OperationalError):
        message = str(error).lower()

        if "locked" in message or "busy" in message:
            return {
                "category": "TRANSIENT",
                "code": "SQLITE_BUSY",
                "retry_eligible": True,
                "suggested_action": "BOUNDED_RETRY",
            }

    return {
        "category": "UNKNOWN",
        "code": type(error).__name__,
        "retry_eligible": False,
        "suggested_action": "MANUAL_INVESTIGATION",
    }
