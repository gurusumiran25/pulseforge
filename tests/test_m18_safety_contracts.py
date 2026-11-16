"""Permanent M18 safety-contract regression tests."""

from unittest.mock import Mock, patch

import pytest

import services.monitoring.self_healing_orchestrator as planner
import services.monitoring.recovery_controller as controller


RUN_DATE = "2026-11-16"
RUN_ID = "pulseforge-daily:2026-11-16"
EVENTS = 11782


def identity():
    return {
        "run_id": RUN_ID,
        "events_after": EVENTS,
        "database_events": EVENTS,
        "consistent": True,
    }


def metrics():
    return {
        "storage": {
            "events": {"row_count": EVENTS}
        }
    }


def snapshot():
    return {
        "overall_status": "DEGRADED",
        "alerts": [
            {"code": "QUALITY_REPORT_OUTDATED"}
        ],
    }


def run_planner(
    *,
    first=None,
    second=None,
    count=EVENTS,
    builder_error=None,
):
    first = identity() if first is None else first
    second = identity() if second is None else second

    collected = metrics()
    collected["storage"]["events"]["row_count"] = count

    verify = Mock(side_effect=[first, second])
    collect = Mock(return_value=collected)

    if builder_error is None:
        build = Mock(return_value=snapshot())
    else:
        build = Mock(side_effect=builder_error)

    policy = Mock(return_value={
        "authorized": False,
        "action": "NONE",
    })

    with (
        patch.object(planner, "verify_run_consistency", verify),
        patch.object(planner, "collect_metrics", collect),
        patch.object(planner, "build_snapshot", build),
        patch.object(planner, "evaluate_recovery", policy),
    ):
        return (
            planner.plan_self_healing(run_date=RUN_DATE),
            verify,
            collect,
            build,
            policy,
        )


def test_preview_is_read_only_and_default_deny():
    result, verify, collect, build, policy = run_planner()

    assert result["mode"] == "PREVIEW"
    assert result["run_id"] == RUN_ID
    assert result["event_count"] == EVENTS
    assert result["recovery_executed"] is False
    assert result["snapshot_persisted"] is False
    assert result["quality_report_persisted"] is False

    assert verify.call_count == 2
    collect.assert_called_once()
    build.assert_called_once()
    policy.assert_called_once_with(
        alert_code="QUALITY_REPORT_OUTDATED",
        automatic_recovery_enabled=False,
    )


@pytest.mark.parametrize(
    "options",
    [
        {"preview": False},
        {"automatic_recovery_enabled": True},
        {"persist": True},
    ],
)
def test_unauthorized_modes_rejected_before_data_access(options):
    with patch.object(
        planner, "verify_run_consistency"
    ) as verify:
        with pytest.raises(PermissionError):
            planner.plan_self_healing(
                run_date=RUN_DATE,
                **options,
            )
        verify.assert_not_called()


def test_event_count_drift_fails_closed():
    with patch.object(
        planner,
        "verify_run_consistency",
        return_value=identity(),
    ), patch.object(
        planner,
        "collect_metrics",
        return_value={
            "storage": {
                "events": {"row_count": EVENTS + 1}
            }
        },
    ), patch.object(
        planner, "build_snapshot"
    ) as build:
        with pytest.raises(RuntimeError):
            planner.plan_self_healing(run_date=RUN_DATE)

        build.assert_not_called()


def test_run_identity_change_fails_closed():
    changed = identity()
    changed["run_id"] = "different-run"

    with patch.object(
        planner,
        "verify_run_consistency",
        side_effect=[identity(), changed],
    ), patch.object(
        planner, "collect_metrics", return_value=metrics()
    ), patch.object(
        planner, "build_snapshot", return_value=snapshot()
    ):
        with pytest.raises(RuntimeError):
            planner.plan_self_healing(run_date=RUN_DATE)


def test_failed_consistency_fails_closed():
    changed = identity()
    changed["consistent"] = False

    with patch.object(
        planner,
        "verify_run_consistency",
        side_effect=[identity(), changed],
    ), patch.object(
        planner, "collect_metrics", return_value=metrics()
    ), patch.object(
        planner, "build_snapshot", return_value=snapshot()
    ):
        with pytest.raises(RuntimeError):
            planner.plan_self_healing(run_date=RUN_DATE)


def test_snapshot_error_propagates():
    with patch.object(
        planner,
        "verify_run_consistency",
        return_value=identity(),
    ), patch.object(
        planner, "collect_metrics", return_value=metrics()
    ), patch.object(
        planner,
        "build_snapshot",
        side_effect=RuntimeError("Injected failure"),
    ):
        with pytest.raises(RuntimeError, match="Injected failure"):
            planner.plan_self_healing(run_date=RUN_DATE)


def test_recovery_default_deny():
    operation = Mock()

    with pytest.raises(PermissionError):
        controller.run_authorized_quality_recovery(
            alert_code="QUALITY_REPORT_MISSING",
            operation=operation,
            execute=True,
        )

    operation.assert_not_called()


def test_recovery_preview_never_executes():
    operation = Mock()

    result = controller.run_authorized_quality_recovery(
        alert_code="QUALITY_REPORT_MISSING",
        operation=operation,
        automatic_recovery_enabled=True,
        execute=False,
    )

    assert result["executed"] is False
    operation.assert_not_called()


def test_critical_recovery_rejected():
    operation = Mock()

    with pytest.raises(PermissionError):
        controller.run_authorized_quality_recovery(
            alert_code="QUALITY_CRITICAL",
            operation=operation,
            automatic_recovery_enabled=True,
            execute=True,
        )

    operation.assert_not_called()
