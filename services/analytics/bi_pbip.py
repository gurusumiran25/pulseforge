"""Assemble candidate PBIP files. Desktop compatibility is not certified."""
import json
from pathlib import Path

from services.analytics.bi_pbir import report_sources
from services.analytics.bi_tmdl import ROOT, generate_model_sources


def package_sources(root=ROOT, snapshot_id="UNCONFIGURED"):
    model = "PulseForge.SemanticModel/"
    report = "PulseForge.Report/"
    def encode(value):
        return json.dumps(value, indent=2) + "\n"
    files = {
        "PulseForge.pbip": encode({"version": "1.0", "artifacts": [{"report": {"path": "PulseForge.Report"}}], "settings": {"enableAutoRecovery": True}}),
        model + "definition.pbism": encode({"version": "4.0", "settings": {}}),
        model + "definition/database.tmdl": "database\n\tcompatibilityLevel: 1600\n",
        model + "definition/model.tmdl": "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: en-US\n",
        report + "definition.pbir": encode({"version": "4.0", "datasetReference": {"byPath": {"path": "../PulseForge.SemanticModel"}}}),
        ".gitignore": "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n",
    }
    sources = generate_model_sources(root, snapshot_id)
    files.update({model + "definition/" + path: data for path, data in sources.items()})
    files.update({report + 'definition/' + path: data for path, data in report_sources(root).items()})
    return files


def write_package(destination, root=ROOT, snapshot_id="UNCONFIGURED"):
    destination = Path(destination)
    files = package_sources(root, snapshot_id)
    destination.mkdir(parents=True, exist_ok=False)
    for path, data in files.items():
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data, encoding="utf-8")
    return sorted(files)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination")
    parser.add_argument("--snapshot-id", default="UNCONFIGURED")
    args = parser.parse_args()
    write_package(args.destination, snapshot_id=args.snapshot_id)
