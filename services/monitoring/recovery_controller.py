"""Fail-closed quality recovery authorization controller."""

from services.monitoring.recovery_policy import evaluate_recovery


QUALITY_ALERTS = frozenset({
    "QUALITY_REPORT_MISSING",
    "QUALITY_REPORT_OUTDATED",
})


def run_authorized_quality_recovery(
    *,
    alert_code,
    operation,
    automatic_recovery_enabled=False,
    execute=False,
):
    """Authorize and optionally execute one quality recovery operation."""

    if not isinstance(alert_code, str):
        raise TypeError("alert_code must be a string")

    if not callable(operation):
        raise TypeError("operation must be callable")

    if type(automatic_recovery_enabled) is not bool:
        raise TypeError("automatic_recovery_enabled must be boolean")

    if type(execute) is not bool:
        raise TypeError("execute must be boolean")

    decision = evaluate_recovery(
        alert_code=alert_code,
        automatic_recovery_enabled=automatic_recovery_enabled,
    )

    authorized = (
        alert_code in QUALITY_ALERTS
        and decision["authorized"] is True
        and decision["action"] == "REFRESH_QUALITY_REPORT"
    )

    if not execute:
        return {
            "mode": "PREVIEW",
            "authorized": authorized,
            "executed": False,
            "decision": decision,
        }

    if not automatic_recovery_enabled or not authorized:
        raise PermissionError(
            "Quality recovery is not authorized"
        )

    result = operation()

    return {
        "mode": "EXECUTED",
        "authorized": True,
        "executed": True,
        "decision": decision,
        "result": result,
    }
