"""Validate exported BI data against the M87 relationship contract."""
import csv
import io
import json
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[2] / "powerbi/model/schema.json"


def validate_model(tables):
    model = json.loads(SCHEMA.read_text(encoding="utf-8"))
    grains = {**model["dimensions"], **model["facts"]}
    if set(tables) != {name + ".csv" for name in grains}:
        raise ValueError("Unexpected model tables")
    rows = {}
    keys = {}
    for name, grain in grains.items():
        reader = csv.DictReader(io.StringIO(tables[name + ".csv"].decode("utf-8")))
        if not set(grain).issubset(reader.fieldnames or []):
            raise ValueError(f"Missing grain columns: {name}")
        rows[name] = list(reader)
        keys[name] = set()
        for row in rows[name]:
            key = tuple(row[k] for k in grain)
            if not all(key) or key in keys[name]:
                raise ValueError(f"Invalid grain: {name}")
            keys[name].add(key)
    for rel in model["relationships"]:
        dim, fact, key = rel["dimension"], rel["fact"], rel["key"]
        if model["dimensions"][dim] != [key] or rel["cardinality"] != "one-to-many" or rel["filter"] != "single":
            raise ValueError("Invalid relationship contract")
        for row in rows[fact]:
            if (row.get(key),) not in keys[dim]:
                raise ValueError(f"Orphan foreign key: {fact}.{key}")
    return {name: len(data) for name, data in rows.items()}
