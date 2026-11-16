"""Conservative recovery authorization policies for PulseForge M18.

This module makes decisions only. It never executes recovery.
"""

from services.monitoring.failure_classifier import classify_failure


ALLOWED_ACTIONS = frozenset({
    "REFRESH_QUALITY_REPORT",
    "BOUNDED_RETRY",
})


def decide_recovery(
    classification,
    *,
    automatic_recovery_enabled=False,
):
    """Return an explicit, fail-closed recovery decision."""

    if not isinstance(classification, dict):
        raise TypeError("classification must be a dictionary")

    category = classification.get("category")
    code = classification.get("code")
    action = classification.get("suggested_action")

    decision = {
        "failure_code": code,
        "category": category,
        "action": "NONE",
        "authorized": False,
        "reason": "Automatic recovery not authorized",
    }

    if automatic_recovery_enabled is not True:
        decision["reason"] = "Automatic recovery disabled"
        return decision

    if category == "RECOVERABLE" and code in (
        "QUALITY_REPORT_MISSING",
        "QUALITY_REPORT_OUTDATED",
    ) and action == "REFRESH_QUALITY_REPORT":
        return {
            **decision,
            "action": "REFRESH_QUALITY_REPORT",
            "authorized": True,
            "reason": "Quality evidence can be regenerated",
        }

    if (
        category == "TRANSIENT"
        and code == "SQLITE_BUSY"
        and action == "BOUNDED_RETRY"
        and classification.get("retry_eligible") is True
    ):
        return {
            **decision,
            "action": "BOUNDED_RETRY",
            "authorized": True,
            "reason": "Transient lock eligible for bounded retry",
        }

    decision["reason"] = "Failure is not on recovery allowlist"
    return decision


def evaluate_recovery(
    *,
    error=None,
    alert_code=None,
    automatic_recovery_enabled=False,
):
    classification = classify_failure(
        error=error,
        alert_code=alert_code,
    )

    return decide_recovery(
        classification,
        automatic_recovery_enabled=automatic_recovery_enabled,
    )
