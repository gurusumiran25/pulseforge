import pytest
from pydantic import ValidationError

from contracts.event_validation import EventEnvelope


@pytest.fixture
def valid_event():
    return {
        "event_id": "evt_001",
        "event_name": "add_to_cart",
        "schema_version": 1,
        "event_time": "2026-11-10T10:15:30Z",
        "user_id": "usr_synthetic_1042",
        "session_id": "ses_synthetic_8831",
        "source": "web",
        "platform": "desktop",
        "properties": {
            "product_id": "prd_203",
            "quantity": 2,
            "unit_price": 799.0,
            "currency": "INR",
        },
    }


def test_valid_event(valid_event):
    event = EventEnvelope.model_validate(valid_event)
    assert event.event_name == "add_to_cart"
    assert event.properties["quantity"] == 2
    assert event.event_time.utcoffset().total_seconds() == 0


def test_missing_product_id(valid_event):
    del valid_event["properties"]["product_id"]
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(valid_event)


def test_invalid_quantity(valid_event):
    valid_event["properties"]["quantity"] = -2
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(valid_event)


def test_invalid_schema_version(valid_event):
    valid_event["schema_version"] = 2
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(valid_event)


def test_invalid_currency(valid_event):
    valid_event["properties"]["currency"] = "rupees"
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(valid_event)


def test_missing_timezone(valid_event):
    valid_event["event_time"] = "2026-11-10T10:15:30"
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(valid_event)
