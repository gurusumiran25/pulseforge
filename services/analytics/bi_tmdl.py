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


def measure_sources(root=ROOT):
    root = Path(root)
    measures = {}
    for path in ("docs/M88_POWERBI_DAX.md", "powerbi/measures/CUSTOMER_WINDOW.md", "powerbi/measures/DATE_COHORT.md"):
        for block in re.findall(r"```dax\n(.*?)\n```", (root / path).read_text(), re.S):
            for match in re.finditer(r"^([A-Za-z][A-Za-z0-9 ]*) =([^\n]*(?:\n[ \t]+[^\n]*)*)", block, re.M):
                name, expression = match.group(1).strip(), match.group(2).strip()
                if name in measures or not expression:
                    raise ValueError("Invalid measure: " + name)
                measures[name] = expression
    return measures


def generate_model_sources(root=ROOT, snapshot_id="UNCONFIGURED"):
    root = Path(root)
    if snapshot_id != "UNCONFIGURED" and not re.fullmatch(r"[0-9a-f]{64}", snapshot_id):
        raise ValueError("Invalid snapshot ID")
    sources = generate_sources(root)
    lines = ["table FactEvent"]
    for name, expression in measure_sources(root).items():
        lines.extend(["", "\tmeasure '" + name + "' =", *["\t\t" + line for line in expression.splitlines()]])
        if name.endswith("Rate") or name in ("Purchase Conversion", "Session Growth", "Observed Cohort Retention"):
            lines.append("\t\tformatString: 0.00%")
    sources["tables/FactEvent.tmdl"] = "\n".join(lines) + "\n" + sources["tables/FactEvent.tmdl"].split("\n", 1)[1]
    fn = (root / "powerbi/queries/LoadSnapshotTable.pq").read_text()
    sources["expressions.tmdl"] = 'expression SnapshotId = "' + snapshot_id + '" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n\nexpression LoadSnapshotTable =\n' + "\n".join("\t" + line for line in fn.splitlines()) + "\n"
    calendar = re.search(r"```powerquery\n(.*?)\n```", (root / "powerbi/measures/DATE_COHORT.md").read_text(), re.S).group(1)
    sources["tables/DimDate.tmdl"] = sources["tables/DimDate.tmdl"].split("\t\tsource =", 1)[0] + "\t\tsource =\n" + "\n".join("\t\t\t" + line for line in calendar.splitlines()) + "\n"
    sources["tables/CohortDay.tmdl"] = "table CohortDay\n\n\tcolumn Value\n\t\tdataType: int64\n\t\tsourceColumn: [Value]\n\t\tsummarizeBy: none\n\n\tpartition CohortDay = calculated\n\t\tmode: import\n\t\tsource = GENERATESERIES(1,7,1)\n"
    return sources
