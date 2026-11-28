import pytest
from services.analytics.bi_navigation import load_layout, validate_layout
from services.analytics.bi_report import load_report


def test_layout():
    assert validate_layout(load_layout(), load_report()) == 7


@pytest.mark.parametrize("kind", ["overlap", "bounds", "target", "drillthrough", "currency", "index"])
def test_invalid_layout(kind):
    layout = load_layout()
    page = layout["pages"][0]
    if kind == "overlap":
        page["visuals"][1].update(x=24, y=96)
    elif kind == "bounds":
        page["visuals"][0]["width"] = 2000
    elif kind == "target":
        layout["navigation"][0]["target"] = "missing"
    elif kind == "drillthrough":
        layout["drillthrough"][0]["field"] = "missing"
    elif kind == "currency":
        page["currencyControl"] = False
    else:
        page["visuals"][1]["index"] = 0
    with pytest.raises(ValueError):
        validate_layout(layout, load_report())
