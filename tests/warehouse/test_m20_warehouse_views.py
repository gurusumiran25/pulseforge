"""M20.2: deterministic warehouse verification against disposable SQLite only."""
from datetime import datetime, timezone
from pathlib import Path

import pytest

from contracts.event_validation import EventEnvelope
from services.storage.sqlite_store import SQLiteEventStore


SQL_PATH = Path(__file__).resolve().parents[2] / "warehouse/sql/m20_views.sql"


def make_event(event_id, session, name, timestamp, properties):
    return EventEnvelope(
        event_id=event_id,
        event_name=name,
        schema_version=1,
        event_time=datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc),
        user_id=f"user-{session}",
        session_id=session,
        source="m20-test",
        platform="web",
        properties=properties,
    )


@pytest.fixture
def warehouse(tmp_path):
    # No production/automation paths are referenced or opened.
    store = SQLiteEventStore(tmp_path / "warehouse_fixture.db")
    with store.connect() as conn:
        conn.executescript(SQL_PATH.read_text(encoding="utf-8"))
    return store


@pytest.fixture
def populated(warehouse):
    events = [
        make_event("a1", "session-a", "product_viewed", "2026-11-19T23:55:00",
                   {"product_id": "p1", "category": "books", "price": 10, "currency": "INR"}),
        make_event("a2", "session-a", "add_to_cart", "2026-11-19T23:56:00",
                   {"product_id": "p1", "quantity": 1, "unit_price": 10, "currency": "INR"}),
        make_event("a3", "session-a", "checkout_started", "2026-11-20T00:01:00",
                   {"cart_value": 10, "item_count": 1, "currency": "INR"}),
        make_event("a4", "session-a", "payment_succeeded", "2026-11-20T00:02:00",
                   {"order_id": "o1", "amount": 10, "currency": "INR",
                    "payment_method_category": "card"}),
        make_event("b1", "session-b", "product_viewed", "2026-11-20T10:00:00",
                   {"product_id": "p2", "category": "books", "price": 20, "currency": "INR"}),
        make_event("c1", "session-c", "page_view", "2026-11-20T11:00:00",
                   {"page_path": "/"}),
    ]
    for event in events:
        assert warehouse.insert_event(event)
    return warehouse, events


def test_silver_extracts_valid_event_attributes(populated):
    store, _ = populated
    with store.connect() as conn:
        row = conn.execute(
            "SELECT * FROM silver_events WHERE event_id = ?", ("a4",)
        ).fetchone()
        assert row["event_name"] == "payment_succeeded"
        assert row["schema_version"] == 1
        assert row["source"] == "m20-test"
        assert row["platform"] == "web"
        assert row["order_id"] == "o1"
        assert row["payment_amount"] == 10.0
        assert row["currency"] == "INR"
        assert conn.execute("SELECT COUNT(*) FROM silver_events").fetchone()[0] == 6


def test_gold_session_grain_and_independent_stage_flags(populated):
    store, _ = populated
    with store.connect() as conn:
        rows = {
            row["session_id"]: row
            for row in conn.execute("SELECT * FROM gold_session_funnel")
        }
    assert set(rows) == {"session-a", "session-b", "session-c"}
    assert rows["session-a"]["event_count"] == 4
    assert tuple(rows["session-a"][k] for k in
                 ("viewed_product", "added_to_cart", "started_checkout",
                  "completed_payment")) == (1, 1, 1, 1)
    assert tuple(rows["session-b"][k] for k in
                 ("viewed_product", "added_to_cart", "started_checkout",
                  "completed_payment")) == (1, 0, 0, 0)
    assert rows["session-c"]["completed_payment"] == 0


def test_daily_funnel_groups_by_session_start_date_not_payment_date(populated):
    store, _ = populated
    with store.connect() as conn:
        rows = {
            row["cohort_date_utc"]: dict(row)
            for row in conn.execute("SELECT * FROM gold_daily_funnel")
        }
    assert rows["2026-11-19"]["sessions"] == 1
    assert rows["2026-11-19"]["sessions_with_payment"] == 1
    assert rows["2026-11-20"]["sessions"] == 2
    assert rows["2026-11-20"]["sessions_with_product_view"] == 1
    assert rows["2026-11-20"]["sessions_with_payment"] == 0


def test_duplicate_event_id_does_not_inflate_metrics(populated):
    store, events = populated
    assert store.insert_event(events[0]) is False
    with store.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM silver_events").fetchone()[0] == 6
        assert conn.execute(
            "SELECT SUM(event_count) FROM gold_session_funnel"
        ).fetchone()[0] == 6


def test_empty_warehouse_has_no_gold_or_silver_rows(warehouse):
    with warehouse.connect() as conn:
        for view in ("silver_events", "gold_session_funnel", "gold_daily_funnel"):
            assert conn.execute(f"SELECT COUNT(*) FROM {view}").fetchone()[0] == 0


def test_stage_flags_do_not_imply_chronological_funnel(warehouse):
    # A purchase without preceding cart/view is still recorded as a stage flag.
    event = make_event(
        "direct-pay", "session-direct", "payment_succeeded",
        "2026-11-20T12:00:00",
        {"order_id": "direct", "amount": 5, "currency": "INR",
         "payment_method_category": "upi"},
    )
    assert warehouse.insert_event(event)
    with warehouse.connect() as conn:
        row = conn.execute("SELECT * FROM gold_session_funnel").fetchone()
    assert row["completed_payment"] == 1
    assert row["viewed_product"] == 0
    assert row["added_to_cart"] == 0
    assert row["started_checkout"] == 0
