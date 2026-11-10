import json

import pytest

from services.generator.batch_generator import (
    generate_batch,
    save_jsonl,
    summarize_batch,
)


def test_batch_generates_requested_sessions():
    events = generate_batch(sessions=20, seed=42)
    assert len({event.session_id for event in events}) == 20
    assert 60 <= len(events) <= 120


def test_batch_events_have_unique_ids():
    events = generate_batch(sessions=20, seed=42)
    assert len({event.event_id for event in events}) == len(events)


def test_summary_counts_are_consistent():
    events = generate_batch(sessions=20, seed=42)
    summary = summarize_batch(events)

    assert summary["total_sessions"] == 20
    assert summary["total_events"] == len(events)
    assert (
        summary["successful_payments"] + summary["failed_payments"]
        == summary["checkouts"]
    )


def test_jsonl_output(tmp_path):
    events = generate_batch(sessions=5, seed=42)
    output = tmp_path / "events.jsonl"

    save_jsonl(events, output)

    records = [
        json.loads(line)
        for line in output.read_text(encoding="utf-8").splitlines()
    ]

    assert len(records) == len(events)
    assert all(record["schema_version"] == 1 for record in records)


def test_invalid_session_count():
    with pytest.raises(ValueError):
        generate_batch(sessions=0)
