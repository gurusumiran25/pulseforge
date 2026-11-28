"""Generate candidate TMDL table and relationship source from the BI contracts.

Native Microsoft engine validation is required before release.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TYPE_MAP = {"type text": "string", "type date": "dateTime",
            "type datetimezone": "dateTime", "Int64.Type": "int64",
            "Currency.Type": "decimal"}


def generate_sources(root=ROOT):
    root = Path(root)
    schema = json.loads((root / "powerbi/model/schema.json").read_text())
    queries = (root / "powerbi/queries/TABLES.md").read_text()
    sources = {}
    for name in [*schema["dimensions"], *schema["facts"]]:
        match = re.search(r"^## " + name + r"\n\n```powerquery\n(.*?)\n```", queries, re.M | re.S)
        if not match:
            raise ValueError("Missing query: " + name)
        query = match.group(1)
        columns = re.findall(r'\{"([^"]+)", ([^}]+)\}', query)
        if not columns:
            raise ValueError("Missing columns: " + name)
        lines = ["table " + name]
        for column, kind in columns:
            lines.extend(["", "\tcolumn " + column, "\t\tdataType: " + TYPE_MAP[kind],
                          "\t\tsourceColumn: " + column, "\t\tsummarizeBy: none"])
        # Normalize timezone-aware M values to UTC datetime for the tabular engine.
        zoned = [col for col, kind in columns if kind == "type datetimezone"]
        if zoned:
            transforms = ", ".join('{"' + col + '", each DateTimeZone.RemoveZone(DateTimeZone.SwitchZone(_, 0)), type datetime}' for col in zoned)
            query = "Table.TransformColumns(" + query + ", {" + transforms + "})"
        lines.extend(["", "\tpartition " + name + " = m", "\t\tmode: import",
                      "\t\tsource =", "\t\t\t" + query])
        sources["tables/" + name + ".tmdl"] = "\n".join(lines) + "\n"
    relationships = []
    for rel in schema["relationships"]:
        fact, dim, key = rel["fact"], rel["dimension"], rel["key"]
        relationships.extend(["relationship " + fact + "_" + dim,
                              "\tfromColumn: " + fact + "." + key,
                              "\ttoColumn: " + dim + "." + key, ""])
    sources["relationships.tmdl"] = "\n".join(relationships)
    return sources
