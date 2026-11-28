import pytest

from services.analytics.bi_exports import csv_bytes
from services.analytics.bi_model import validate_model


def fixture_tables():
    d, u, s, e, p = "2026-11-28", "synthetic_1", "session_1", "event_1", "P101"
    return {
        "DimDate.csv": csv_bytes(["date_utc"], [(d,)]),
        "DimCustomer.csv": csv_bytes(["user_id"], [(u,)]),
        "DimCurrency.csv": csv_bytes(["currency"], [("INR",)]),
        "DimProduct.csv": csv_bytes(["product_id"], [(p,)]),
        "FactEvent.csv": csv_bytes(["event_id", "date_utc", "user_id"], [(e,d,u)]),
        "FactSession.csv": csv_bytes(["session_id", "date_utc", "user_id"], [(s,d,u)]),
        "FactPayment.csv": csv_bytes(["event_id", "date_utc", "user_id", "currency"], [(e,d,u,"INR")]),
        "FactDailyUser.csv": csv_bytes(["date_utc", "user_id"], [(d,u)]),
        "FactProductView.csv": csv_bytes(["event_id", "date_utc", "user_id", "product_id"], [(e,d,u,p)]),
    }


def test_valid_model():
    assert validate_model(fixture_tables()) == {name[:-4]: 1 for name in fixture_tables()}


@pytest.mark.parametrize("name,fields,rows", [
    ("DimCustomer", ["user_id"], [("synthetic_1",), ("synthetic_1",)]),
    ("DimDate", ["date_utc"], [("",)]),
    ("DimCurrency", ["currency"], [("USD",)]),
    ("DimProduct", ["product_id"], [("P999",)]),
    ("FactDailyUser", ["date_utc", "user_id"], [("2026-11-28","synthetic_1")]*2),
])
def test_invalid_model(name, fields, rows):
    tables = fixture_tables()
    tables[name + ".csv"] = csv_bytes(fields, rows)
    with pytest.raises(ValueError):
        validate_model(tables)


def test_missing_table():
    tables = fixture_tables()
    del tables["DimDate.csv"]
    with pytest.raises(ValueError):
        validate_model(tables)
