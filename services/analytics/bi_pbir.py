"""Candidate PBIR source generation; native schema/engine acceptance is pending."""
import json
from pathlib import Path
from services.analytics.bi_tmdl import ROOT

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"


def projection(table, name, measure=False):
    kind = "Measure" if measure else "Column"
    return {"field": {kind: {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}},
            "queryRef": table + "." + name, "nativeQueryRef": name}


def visual_source(name, kind, position, roles):
    return {"$schema": SCHEMA + "visualContainer/2.0.0/schema.json",
            "name": name, "position": position,
            "visual": {"visualType": kind, "query": {"queryState": {
                role: {"projections": values} for role, values in roles.items() if values
            }}, "drillFilterOtherVisuals": True}}


def report_sources(root=ROOT):
    root = Path(root)
    spec = json.loads((root / "powerbi/report/report_spec.json").read_text())
    layout = json.loads((root / "powerbi/report/navigation_layout.json").read_text())
    positions = {p["id"]: p for p in layout["pages"]}
    files = {}
    def put(path, obj):
        files[path] = json.dumps(obj, indent=2) + "\n"
    put("version.json", {"$schema": SCHEMA + "versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    put("report.json", {"$schema": SCHEMA + "report/2.0.0/schema.json"})
    ids = [p["id"] for p in spec["pages"]]
    put("pages/pages.json", {"$schema": SCHEMA + "pagesMetadata/1.0.0/schema.json", "pageOrder": ids, "activePageName": ids[0]})
    for page in spec["pages"]:
        pid = page["id"]
        prefix = "pages/" + pid + "/"
        put(prefix + "page.json", {"$schema": SCHEMA + "page/2.0.0/schema.json", "name": pid,
            "displayName": page["title"], "displayOption": "FitToPage", **spec["canvas"]})
        for pos in positions[pid]["visuals"]:
            i = pos["index"]
            v = page["visuals"][i]
            fields = [projection(*f.split(".", 1)) for f in v["fields"]]
            measures = [projection("FactEvent", m, True) for m in v["measures"]]
            kind = v["type"]
            if kind == "matrix":
                native, roles = "pivotTable", {"Rows": fields[:1], "Columns": fields[1:], "Values": measures}
            elif kind == "table":
                native, roles = "tableEx", {"Values": fields + measures}
            elif kind in ("cards", "funnel") or not fields:
                # Preserve every metric using a table fallback until native multi-measure funnel is validated.
                native, roles = "tableEx", {"Values": fields + measures}
            else:
                native = {"line": "lineChart", "bar": "clusteredBarChart"}[kind]
                roles = {"Category": fields, "Y": measures}
            name = "visual" + str(i)
            geometry = {k: pos[k] for k in ("x", "y", "width", "height")}
            put(prefix + "visuals/" + name + "/visual.json", visual_source(name, native, {**geometry, "z": i, "tabOrder": i}, roles))
        for j, field in enumerate([spec["dateSlicer"]] + (["DimCurrency.currency"] if page.get("currency") else [])):
            name = "slicer" + str(j)
            put(prefix + "visuals/" + name + "/visual.json", visual_source(name, "slicer",
                {"x": 24 + 420*j, "y": 8, "width": 400, "height": 72, "z": 10+j, "tabOrder": 10+j},
                {"Values": [projection(*field.split(".", 1))]}))
    return files
