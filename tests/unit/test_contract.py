import json
from pathlib import Path


def test_event_contract_has_required_fields():
    path = Path(__file__).resolve().parents[2] / "contracts/events/event_envelope_v1.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == 1
    assert "event_id" in schema["required"]
    assert "event_time" in schema["required"]
    assert "ingested_at" not in schema["required"]  # assigned by ingestion API
