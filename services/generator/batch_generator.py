import argparse
import json
from collections import Counter
from pathlib import Path

from services.generator.journey_generator import generate_customer_journey


def generate_batch(sessions: int, seed: int = 42):
    if sessions <= 0:
        raise ValueError("sessions must be greater than zero")

    events = []
    for index in range(sessions):
        events.extend(generate_customer_journey(seed=seed + index))

    return events


def summarize_batch(events):
    counts = Counter(event.event_name for event in events)
    sessions = len({event.session_id for event in events})

    def percentage(numerator, denominator):
        return round(100 * numerator / denominator, 2) if denominator else 0.0

    return {
        "total_sessions": sessions,
        "total_events": len(events),
        "product_views": counts["product_viewed"],
        "add_to_cart": counts["add_to_cart"],
        "checkouts": counts["checkout_started"],
        "successful_payments": counts["payment_succeeded"],
        "failed_payments": counts["payment_failed"],
        "cart_addition_rate_pct": percentage(counts["add_to_cart"], sessions),
        "checkout_rate_pct": percentage(counts["checkout_started"], sessions),
        "purchase_conversion_rate_pct": percentage(
            counts["payment_succeeded"], sessions
        ),
        "payment_failure_rate_pct": percentage(
            counts["payment_failed"],
            counts["payment_succeeded"] + counts["payment_failed"],
        ),
    }


def save_jsonl(events, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for event in events:
            file.write(event.model_dump_json() + "\n")

    return path


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic PulseForge customer journeys"
    )
    parser.add_argument("--sessions", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output",
        default="data/generated/customer_events.jsonl",
    )

    args = parser.parse_args()

    events = generate_batch(args.sessions, args.seed)
    path = save_jsonl(events, args.output)
    summary = summarize_batch(events)

    print(f"Dataset saved to: {path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
