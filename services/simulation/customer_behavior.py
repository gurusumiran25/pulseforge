from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class CustomerBehavior:
    segment: str
    purchase_probability: float
    return_probability: float
    average_basket_multiplier: float


PROFILES = {
    "casual_browser": CustomerBehavior(
        "casual_browser", 0.05, 0.10, 0.70
    ),
    "price_sensitive": CustomerBehavior(
        "price_sensitive", 0.15, 0.25, 0.85
    ),
    "frequent_buyer": CustomerBehavior(
        "frequent_buyer", 0.40, 0.65, 1.20
    ),
    "high_value": CustomerBehavior(
        "high_value", 0.55, 0.75, 2.00
    ),
}

SEGMENT_WEIGHTS = (
    ("casual_browser", 40),
    ("price_sensitive", 30),
    ("frequent_buyer", 20),
    ("high_value", 10),
)


def get_customer_behavior(customer_id: str) -> CustomerBehavior:
    if not isinstance(customer_id, str) or not customer_id.strip():
        raise ValueError("customer_id must be a non-empty string")

    digest = sha256(customer_id.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big") % 100

    cumulative = 0
    for segment, weight in SEGMENT_WEIGHTS:
        cumulative += weight
        if bucket < cumulative:
            return PROFILES[segment]

    raise RuntimeError("Invalid segment weights")
