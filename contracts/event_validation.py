from datetime import datetime, timezone
from typing import Any, Dict, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EventName = Literal[
    "page_view", "search_performed", "product_viewed",
    "add_to_cart", "checkout_started", "payment_succeeded",
    "payment_failed", "order_refunded",
]

REQUIRED_PROPERTIES = {
    "page_view": {"page_path"},
    "search_performed": {"search_category", "result_count"},
    "product_viewed": {"product_id", "category", "price", "currency"},
    "add_to_cart": {"product_id", "quantity", "unit_price", "currency"},
    "checkout_started": {"cart_value", "item_count", "currency"},
    "payment_succeeded": {
        "order_id", "amount", "currency", "payment_method_category"
    },
    "payment_failed": {"order_id", "failure_code_category"},
    "order_refunded": {
        "order_id", "refund_amount", "currency", "reason_category"
    },
}


class EventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    event_name: EventName
    schema_version: Literal[1]
    event_time: datetime
    user_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    properties: Dict[str, Any]
    ingested_at: datetime | None = None

    @field_validator("event_time", "ingested_at")
    @classmethod
    def normalize_utc(cls, value):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must include timezone information")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_properties(self):
        required = REQUIRED_PROPERTIES[self.event_name]
        missing = required - self.properties.keys()

        if missing:
            raise ValueError(f"Missing properties: {sorted(missing)}")

        for key in required:
            value = self.properties[key]
            if value is None or (
                isinstance(value, str) and not value.strip()
            ):
                raise ValueError(f"{key} cannot be empty")

        for key in ("quantity", "item_count"):
            if key in self.properties:
                value = self.properties[key]
                if type(value) is not int or value <= 0:
                    raise ValueError(f"{key} must be a positive integer")

        if "result_count" in self.properties:
            value = self.properties["result_count"]
            if type(value) is not int or value < 0:
                raise ValueError("result_count must be non-negative")

        for key in (
            "price", "unit_price", "cart_value", "amount", "refund_amount"
        ):
            if key in self.properties:
                value = self.properties[key]
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not float("-inf") < value < float("inf")
                    or value < 0
                ):
                    raise ValueError(f"{key} must be a finite non-negative number")

        if "currency" in self.properties:
            currency = self.properties["currency"]
            if (
                not isinstance(currency, str)
                or len(currency) != 3
                or not currency.isascii()
                or not currency.isalpha()
                or not currency.isupper()
            ):
                raise ValueError("currency must be a three-letter uppercase code")

        return self
