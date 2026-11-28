"""Static report contract validation; not a native Power BI renderer."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEASURE_FILES = ("docs/M88_POWERBI_DAX.md", "powerbi/measures/CUSTOMER_WINDOW.md",
                 "powerbi/measures/DATE_COHORT.md")
FIELDS = {"DimDate.date_utc", "DimCustomer.user_id", "DimProduct.category",
          "DimProduct.product_id", "FactEvent.event_name", "CohortDay.Value"}
MONEY = {"Gross Revenue", "Refund Amount", "Net Revenue", "Monetary Value", "RFM Segment"}
PAGES = {"executive", "journey", "payments", "customers", "products", "quality", "insights"}


def measure_names():
    names = set()
    for path in MEASURE_FILES:
        for block in re.findall(r"```dax\n(.*?)```", (ROOT / path).read_text(), re.S):
            names.update(re.findall(r"^([A-Za-z][A-Za-z0-9 ]*?)\s*=", block, re.M))
    return names


def validate_report(spec):
    pages = spec["pages"]
    if len(pages) != 7 or {p["id"] for p in pages} != PAGES:
        raise ValueError("Invalid page set")
    if spec["dateSlicer"] != "DimDate.date_utc":
        raise ValueError("Invalid date slicer")
    names = measure_names()
    for page in pages:
        if not page["visuals"]:
            raise ValueError("Empty page")
        for visual in page["visuals"]:
            if visual["type"] not in {"cards", "line", "bar", "funnel", "matrix", "table"}:
                raise ValueError("Unknown visual type")
            measures = set(visual["measures"])
            if not measures or measures - names:
                raise ValueError("Unknown or missing measure")
            if set(visual["fields"]) - FIELDS:
                raise ValueError("Unknown field")
            if measures & MONEY and not page.get("currency"):
                raise ValueError("Missing currency control")
    return sum(len(p["visuals"]) for p in pages)


def load_report():
    return json.loads((ROOT / "powerbi/report/report_spec.json").read_text())
