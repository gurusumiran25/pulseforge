"""Product-view projection for the synthetic single-product journey."""
import csv
import io
import json
from services.analytics.bi_exports import csv_bytes
from services.generator.journey_generator import PRODUCTS
from services.storage.sqlite_store import SQLiteEventStore

def add_product_tables(tables, db_path):
    catalog = {p["id"]: p["category"] for p in PRODUCTS}
    events = {r["event_id"]: r for r in csv.DictReader(io.StringIO(tables["FactEvent.csv"].decode()))}
    expected = {k for k,v in events.items() if v["event_name"] == "product_viewed"}
    seen, rows = set(), []
    with SQLiteEventStore(db_path).connect() as con:
        for record in con.execute("SELECT payload FROM events WHERE event_name = 'product_viewed'"):
            event = json.loads(record["payload"])
            eid = event["event_id"]
            props = event["properties"]
            product = props["product_id"]
            if eid not in expected or eid in seen or catalog.get(product) != props["category"]:
                raise ValueError("Invalid product projection")
            e = events[eid]
            if e["session_id"] != event["session_id"] or e["user_id"] != event["user_id"]:
                raise ValueError("Product event identity mismatch")
            seen.add(eid)
            rows.append((eid, e["session_id"], e["user_id"], e["date_utc"], product))
    if seen != expected:
        raise ValueError("Missing product views")
    return {**tables,
            "FactProductView.csv": csv_bytes(("event_id","session_id","user_id","date_utc","product_id"), sorted(rows)),
            "DimProduct.csv": csv_bytes(("product_id","category"), sorted(catalog.items()))}
