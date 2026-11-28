import pytest

from services.analytics.bi_tmdl import generate_model_sources, measure_sources


def test_measure_completeness():
    measures = measure_sources()
    assert len(measures) == 34
    assert "Observed Cohort Retention" in measures
    assert "RETURN IF" in measures["Observed Cohort Retention"]
    assert "HASONEVALUE" in measures["Net Revenue"]


def test_model_sources():
    sources = generate_model_sources(snapshot_id="a" * 64)
    assert len([p for p in sources if p.startswith("tables/")]) == 10
    assert sources["relationships.tmdl"].count("relationship ") == 12
    assert sources["tables/FactEvent.tmdl"].count("\tmeasure ") == 34
    assert "List.Dates" in sources["tables/DimDate.tmdl"]
    assert "GENERATESERIES" in sources["tables/CohortDay.tmdl"]
    assert "DateTimeZone.SwitchZone" in sources["tables/FactEvent.tmdl"]
    assert "a" * 64 in sources["expressions.tmdl"]
    assert sources == generate_model_sources(snapshot_id="a" * 64)


@pytest.mark.parametrize("value", ["../bad", "a" * 63, "G" * 64])
def test_invalid_snapshot(value):
    with pytest.raises(ValueError, match="snapshot"):
        generate_model_sources(snapshot_id=value)


def test_semantic_model_package(tmp_path):
    from services.analytics.bi_tmdl import write_semantic_model

    target = tmp_path / "PulseForge.SemanticModel"
    assert write_semantic_model(target, snapshot_id="a" * 64) == target
    assert (target / "definition.pbism").is_file()
    model = (target / "definition/model.tmdl").read_text()
    assert model.count("ref table ") == 10
    assert (target / "definition/database.tmdl").is_file()
    assert len(list((target / "definition/tables").glob("*.tmdl"))) == 10
    with pytest.raises(FileExistsError):
        write_semantic_model(target)
