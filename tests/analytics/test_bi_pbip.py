import json

import pytest

from services.analytics.bi_pbip import package_sources, write_package
from services.analytics.bi_tmdl import measure_sources


def test_package(tmp_path):
    files = package_sources(snapshot_id="a" * 64)
    assert files == package_sources(snapshot_id="a" * 64)
    dest = tmp_path / "PulseForge"
    assert write_package(dest, snapshot_id="a" * 64) == sorted(files)
    for path, value in files.items():
        assert (dest / path).read_text() == value
        if path.endswith((".json", ".pbip", ".pbir", ".pbism")):
            json.loads(value)
    with pytest.raises(FileExistsError):
        write_package(dest)


def test_report_bindings():
    files = package_sources()
    prefix = "PulseForge.Report/definition/"
    pages = json.loads(files[prefix + "pages/pages.json"])["pageOrder"]
    assert len(pages) == len(set(pages)) == 7
    visuals = [json.loads(v) for k, v in files.items() if k.endswith("/visual.json")]
    assert len(visuals) == 41
    assert sum(v["visual"]["visualType"] == "pageNavigator" for v in visuals) == 7
    assert sum(v["visual"]["visualType"] == "slicer" for v in visuals) == 10
    measures = measure_sources()
    for v in visuals:
        p = v["position"]
        assert 0 <= p["x"] < p["x"] + p["width"] <= 1280
        assert 0 <= p["y"] < p["y"] + p["height"] <= 720
        for role in v["visual"]["query"]["queryState"].values():
            for projection in role["projections"]:
                field = projection["field"]
                if "Measure" in field:
                    assert field["Measure"]["Property"] in measures
                else:
                    col = field["Column"]
                    table = col["Expression"]["SourceRef"]["Entity"]
                    assert "column " + col["Property"] in files[
                        "PulseForge.SemanticModel/definition/tables/" + table + ".tmdl"
                    ]


def test_native_report_features():
    files = package_sources()
    prefix = "PulseForge.Report/definition/"
    report = json.loads(files[prefix + "report.json"])
    theme = report["themeCollection"]["customTheme"]["name"]
    assert files["PulseForge.Report/StaticResources/RegisteredResources/" + theme] == files[theme]
    for page in ("journey", "payments"):
        doc = json.loads(files[prefix + "pages/" + page + "/page.json"])
        assert doc["pageBinding"]["type"] == "Drillthrough"
        assert doc["pageBinding"]["parameters"][0]["boundFilter"] == doc["filterConfig"]["filters"][0]["name"]
    visuals = [json.loads(v)["visual"] for k, v in files.items() if k.endswith("/visual.json")]
    currency = [v for v in visuals if v["visualType"] == "slicer" and "objects" in v]
    assert len(currency) == 3
    assert all(v["objects"]["selection"][0]["properties"]["singleSelect"]["expr"]["Literal"]["Value"] == "true" for v in currency)
    assert sum(v["visualType"] == "funnel" for v in visuals) == 2
    growth = [v for v in visuals if "calloutValue" in v.get("objects", {})]
    assert len(growth) == 1
