import json
from services.analytics.bi_report import ROOT, load_report


def load_layout():
    return json.loads((ROOT / "powerbi/report/navigation_layout.json").read_text())


def validate_layout(layout, report):
    pages = {p["id"]: p for p in report["pages"]}
    width, height = report["canvas"]["width"], report["canvas"]["height"]
    if layout["canvas"] != report["canvas"]:
        raise ValueError("Canvas mismatch")
    for entries, key in [(layout["navigation"], "target"), (layout["pages"], "id")]:
        if len(entries) != len(pages) or {e[key] for e in entries} != set(pages):
            raise ValueError("Invalid page targets")
    for page in layout["pages"]:
        source = pages[page["id"]]
        visuals = page["visuals"]
        if sorted(v["index"] for v in visuals) != list(range(len(source["visuals"]))):
            raise ValueError("Missing or duplicate visual")
        if page["currencyControl"] != bool(source.get("currency")):
            raise ValueError("Currency control mismatch")
        for i, v in enumerate(visuals):
            x, y, w, h = (v[k] for k in ("x", "y", "width", "height"))
            if min(x, y) < 0 or min(w, h) <= 0 or x+w > width or y+h > height:
                raise ValueError("Visual outside canvas")
            for other in visuals[:i]:
                if x < other["x"]+other["width"] and other["x"] < x+w and y < other["y"]+other["height"] and other["y"] < y+h:
                    raise ValueError("Overlapping visuals")
    for link in layout["drillthrough"]:
        if link["source"] not in pages or link["target"] not in pages or link["source"] == link["target"] or link["field"] != report["dateSlicer"]:
            raise ValueError("Invalid drillthrough")
    return len(pages)
