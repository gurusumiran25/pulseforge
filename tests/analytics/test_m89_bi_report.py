import pytest
from services.analytics.bi_report import load_report, validate_report


def test_report_contract():
    assert validate_report(load_report()) == 24


@pytest.mark.parametrize("kind", ["measure", "field", "currency", "page", "visual"])
def test_invalid_report(kind):
    spec = load_report()
    page = spec["pages"][0]
    if kind == "measure":
        page["visuals"][0]["measures"].append("Missing Measure")
    elif kind == "field":
        page["visuals"][0]["fields"].append("Unknown.column")
    elif kind == "currency":
        page["currency"] = False
    elif kind == "page":
        spec["pages"].pop()
    else:
        page["visuals"][0]["type"] = "unknown"
    with pytest.raises(ValueError):
        validate_report(spec)
