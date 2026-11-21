"""Exercise Streamlit script execution and visible metric widgets via AppTest.

Unlike the existing HTTP health smoke test, this executes the app's script.
"""
import csv
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[2] / "apps/dashboard/streamlit_app.py"


def test_demo_dashboard_renders_kpis():
    at = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not at.exception, [str(item.message) for item in at.exception]
    values = {metric.label: metric.value for metric in at.metric}
    assert {"Events", "Sessions", "Users", "Sessions with payment"} <= values.keys()
    assert int(values["Events"]) > 0
    assert int(values["Sessions"]) > 0


def test_configured_generated_csv_renders_and_preserves_cohort(monkeypatch, tmp_path):
    path = tmp_path / "generated_events.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["event_id", "event_name", "session_id", "user_id", "event_time"])
        writer.writerow(["m31-1", "product_viewed", "session-a", "user-a", "2026-11-20T23:59:00Z"])
        writer.writerow(["m31-2", "payment_succeeded", "session-a", "user-a", "2026-11-21T00:01:00Z"])
    monkeypatch.setenv("PULSEFORGE_DASHBOARD_CSV", str(path))
    at = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not at.exception, [str(item.message) for item in at.exception]
    values = {metric.label: metric.value for metric in at.metric}
    assert int(values["Events"]) == 2
    assert int(values["Sessions"]) == 1
    assert int(values["Users"]) == 1
    assert int(values["Sessions with payment"]) == 1


def test_missing_configured_source_shows_user_facing_error(monkeypatch, tmp_path):
    monkeypatch.setenv("PULSEFORGE_DASHBOARD_CSV", str(tmp_path / "missing.csv"))
    at = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not at.exception, [str(item.message) for item in at.exception]
    assert any("Unable to load event CSV" in item.proto.body for item in at.error)
