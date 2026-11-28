"""Generate independent expected KPI evidence for a verified BI snapshot."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

from services.analytics.bi_kpis import reference_kpis
from services.analytics.bi_refresh import verify_refresh


def expected_evidence(root, now=None):
    root = Path(root)
    verified = verify_refresh(root, now=now)
    folder = root / verified["snapshot"]
    manifest = json.loads((folder / "manifest.json").read_bytes())
    tables = {}
    for name, meta in manifest["files"].items():
        data = (folder / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != meta["sha256"]:
            raise ValueError("Snapshot changed during acceptance")
        tables[name] = data
    currencies = sorted(r["currency"] for r in csv.DictReader(
        io.StringIO(tables["DimCurrency.csv"].decode())))
    return {
        **verified,
        "evidence_type": "python_reference_not_native_runtime",
        "scope": "entire_snapshot",
        "unfiltered": reference_kpis(tables),
        "by_currency": {c: reference_kpis(tables, c) for c in currencies},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    evidence = expected_evidence(args.snapshot_root)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, indent=2, default=str)
        stream.write("\n")


if __name__ == "__main__":
    main()
