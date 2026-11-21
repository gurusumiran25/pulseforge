"""M29 configured dashboard CSV source remains compatible with generated data."""
from apps.dashboard.metrics import load_events, summarize


def test_generated_csv_can_be_used_as_dashboard_source(tmp_path):
    from csv import writer

    path = tmp_path / "generated.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        rows = writer(handle)
        rows.writerow(["event_id", "event_name", "session_id", "user_id", "event_time"])
        rows.writerow(["evt1", "product_viewed", "s1", "u1", "2026-11-20T23:59:00+00:00"])
        rows.writerow(["evt2", "payment_succeeded", "s1", "u1", "2026-11-21T00:01:00+00:00"])
    result = summarize(load_events(path))
    assert result["events"] == 2
    assert result["sessions"] == 1
    assert result["paid_sessions"] == 1
    assert result["daily_funnel"][0]["date"] == "2026-11-20"
