import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from services.analytics.bi_snapshot import publish_snapshot


def test_idempotent_snapshot(tmp_path):
    tables = {"FactEvent.csv": b"event_id\n1\n"}
    first = publish_snapshot(tmp_path, tables)
    assert publish_snapshot(tmp_path, tables) == first
    assert json.loads((tmp_path / "current.json").read_text())["snapshot"] == first
    assert (tmp_path / first / "FactEvent.csv").read_bytes() == tables["FactEvent.csv"]


def test_invalid_input_preserves_pointer(tmp_path):
    first = publish_snapshot(tmp_path, {"FactEvent.csv": b"event_id\n1\n"})
    with pytest.raises(ValueError):
        publish_snapshot(tmp_path, {"../bad.csv": b"x"})
    assert json.loads((tmp_path / "current.json").read_text())["snapshot"] == first


def test_corruption_preserves_pointer(tmp_path):
    tables = {"FactEvent.csv": b"event_id\n1\n"}
    first = publish_snapshot(tmp_path, tables)
    second = publish_snapshot(tmp_path, {"FactEvent.csv": b"event_id\n2\n"})
    (tmp_path / first / "FactEvent.csv").write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        publish_snapshot(tmp_path, tables)
    assert json.loads((tmp_path / "current.json").read_text())["snapshot"] == second


def test_concurrent_publishers(tmp_path):
    with ThreadPoolExecutor(max_workers=4) as pool:
        snapshots = list(pool.map(lambda i: publish_snapshot(tmp_path, {"FactEvent.csv": str(i % 2).encode()}), range(12)))
    current = json.loads((tmp_path / "current.json").read_text())["snapshot"]
    assert current in snapshots
    assert len(set(snapshots)) == 2
    assert (tmp_path / current / "manifest.json").is_file()
