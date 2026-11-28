from datetime import datetime, timezone
import json

import pytest

from services.analytics.bi_exports import csv_bytes
from services.analytics.bi_snapshot import publish_snapshot
from services.analytics.bi_refresh import verify_refresh
from test_m87_bi_model import fixture_tables

NOW = datetime(2026, 11, 28, 12, tzinfo=timezone.utc)


def publish(root, timestamp="2026-11-28T10:00:00Z"):
    tables = fixture_tables()
    tables["FactEvent.csv"] = csv_bytes(
        ["event_id", "date_utc", "user_id", "event_time_utc"],
        [("event_1", "2026-11-28", "synthetic_1", timestamp)],
    )
    return publish_snapshot(root, tables)


def test_fresh_snapshot(tmp_path):
    snapshot = publish(tmp_path)
    result = verify_refresh(tmp_path, now=NOW)
    assert result["snapshot"] == snapshot
    assert result["counts"]["FactEvent"] == 1


@pytest.mark.parametrize("timestamp", ["2026-11-25T10:00:00Z", "2026-11-28T13:00:00Z"])
def test_invalid_freshness(tmp_path, timestamp):
    publish(tmp_path, timestamp)
    with pytest.raises(ValueError, match="Stale"):
        verify_refresh(tmp_path, now=NOW)


@pytest.mark.parametrize("name", ["manifest.json", "FactEvent.csv"])
def test_tampered_snapshot(tmp_path, name):
    snapshot = publish(tmp_path)
    with (tmp_path / snapshot / name).open("ab") as handle:
        handle.write(b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        verify_refresh(tmp_path, now=NOW)


def test_invalid_pointer(tmp_path):
    publish(tmp_path)
    (tmp_path / "current.json").write_text(json.dumps({"snapshot": "../escape", "schema_version": 1}))
    with pytest.raises(ValueError, match="pointer"):
        verify_refresh(tmp_path, now=NOW)
