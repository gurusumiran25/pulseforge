"""M79 monitor temporal evidence regressions."""
from scripts.audit_monitor_chain import monitor_evidence


def run(day, hour=2, minute=30, event="schedule", conclusion="success"):
    return {
        "event": event, "status": "completed", "conclusion": conclusion,
        "created_at": f"2026-11-{day:02d}T{hour:02d}:{minute:02d}:00Z",
        "html_url": f"https://example.test/{event}/{day}/{hour}",
    }


def test_two_days_with_both_independent_monitors():
    publisher = [run(22), run(23)]
    health = [run(22, 2, 40, "workflow_run"), run(23, 2, 40, "workflow_run")]
    remote = [run(22, 2, 45, "workflow_run"), run(23, 2, 45, "workflow_run")]
    result = monitor_evidence(publisher, health, remote)
    assert result["verified"]
    assert result["association"] == "temporal_only_not_exact_trigger_proof"


def test_missing_remote_monitor_fails_closed():
    publisher = [run(22), run(23)]
    health = [run(22, 2, 40, "workflow_run"), run(23, 2, 40, "workflow_run")]
    assert not monitor_evidence(publisher, health, [])["verified"]


def test_scheduled_monitor_not_mistaken_for_workflow_run():
    publisher = [run(22), run(23)]
    health = [run(22, 2, 40, "schedule"), run(23, 2, 40, "schedule")]
    remote = [run(22, 2, 45, "workflow_run"), run(23, 2, 45, "workflow_run")]
    assert not monitor_evidence(publisher, health, remote)["verified"]
