"""M78 scheduled publisher evidence regressions."""
from scripts.audit_scheduled_refresh import scheduled_evidence


def run(day, conclusion="success", event="schedule"):
    return {
        "id": day, "event": event, "status": "completed",
        "conclusion": conclusion, "created_at": f"2026-11-{day:02d}T02:30:00Z",
        "html_url": f"https://example.test/{day}",
    }


def test_two_adjacent_successful_scheduled_runs():
    assert scheduled_evidence([run(22), run(23)])["verified"]


def test_gap_does_not_count_as_consecutive():
    assert not scheduled_evidence([run(21), run(23)])["verified"]


def test_failure_breaks_streak():
    assert not scheduled_evidence([run(21), run(22, "failure"), run(23)])["verified"]


def test_manual_run_does_not_count():
    assert not scheduled_evidence([run(22, event="workflow_dispatch"), run(23)])["verified"]


def test_insufficient_history_is_not_verified():
    assert not scheduled_evidence([run(23)])["verified"]
