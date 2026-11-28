"""Curated BI exports from validated synthetic Bronze and payment rows."""
import csv
import io
import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from services.analytics.bi_snapshot import publish_snapshot

EVENTS = {"page_view", "search_performed", "product_viewed", "add_to_cart",
          "checkout_started", "payment_succeeded", "payment_failed", "order_refunded"}

def csv_bytes(fields, rows):
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(fields)
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")

def utc(value):
    t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("Expected timezone-aware event time")
    return t.astimezone(timezone.utc)

def build_tables(events, payments):
    indexed, sessions, activity = {}, defaultdict(list), defaultdict(list)
    for e in events:
        eid, name, sid, uid = (e[k] for k in ("event_id", "event_name", "session_id", "user_id"))
        if not re.fullmatch(r"[0-9a-fA-F-]{36}", eid) or not re.fullmatch(r"session_[0-9a-f]{12}", sid):
            raise ValueError("Invalid synthetic event/session identifier")
        if not re.fullmatch(r"synthetic_[A-Za-z0-9_-]+", uid) or name not in EVENTS or eid in indexed:
            raise ValueError("Invalid synthetic user, event type or duplicate event")
        t = utc(e["event_time"])
        row = (eid, name, sid, uid, t.isoformat(), t.date().isoformat())
        indexed[eid] = row
        sessions[sid].append(row)
        activity[(row[5], uid)].append(row)
    if not indexed:
        raise ValueError("Empty event export")
    facts = []
    for sid, rows in sorted(sessions.items()):
        users = {r[3] for r in rows}
        if len(users) != 1:
            raise ValueError("Session spans multiple users")
        names = {r[1] for r in rows}
        start, end = min(r[4] for r in rows), max(r[4] for r in rows)
        facts.append((sid, next(iter(users)), start, end, start[:10], len(rows),
                      *(int(n in names) for n in ("product_viewed", "add_to_cart", "checkout_started", "payment_succeeded"))))
    paid, seen, currencies = [], set(), set()
    for p in payments:
        eid = p["event_id"]
        e = indexed.get(eid)
        if not e or eid in seen or e[1] not in {"payment_succeeded", "order_refunded"}:
            raise ValueError("Orphan, duplicate or invalid payment")
        if p["event_name"] != e[1] or p["user_id"] != e[3] or utc(p["event_time"]).isoformat() != e[4]:
            raise ValueError("Payment/event mismatch")
        amount = Decimal(str(p["amount"]))
        currency = p["currency"]
        if not amount.is_finite() or amount < 0 or not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("Invalid amount or currency")
        seen.add(eid)
        currencies.add(currency)
        paid.append((eid, e[1], e[2], e[3], e[5], currency, format(amount, "f")))
    if seen != {k for k,v in indexed.items() if v[1] in {"payment_succeeded", "order_refunded"}}:
        raise ValueError("Missing payment sidecar events")
    return {
        "FactEvent.csv": csv_bytes(("event_id","event_name","session_id","user_id","event_time_utc","date_utc"), sorted(indexed.values())),
        "FactSession.csv": csv_bytes(("session_id","user_id","first_event_time","last_event_time","date_utc","event_count","viewed_product","added_to_cart","started_checkout","completed_payment"), facts),
        "FactPayment.csv": csv_bytes(("event_id","event_name","session_id","user_id","date_utc","currency","amount"), sorted(paid)),
        "FactDailyUser.csv": csv_bytes(("date_utc","user_id","sessions","events"), [(d,u,len({r[2] for r in rows}),len(rows)) for (d,u),rows in sorted(activity.items())]),
        "DimDate.csv": csv_bytes(("date_utc",), [(d,) for d in sorted({r[5] for r in indexed.values()})]),
        "DimCustomer.csv": csv_bytes(("user_id",), [(u,) for u in sorted({r[3] for r in indexed.values()})]),
        "DimCurrency.csv": csv_bytes(("currency",), [(c,) for c in sorted(currencies)]),
    }

def publish_bi(root, events, payments):
    return publish_snapshot(root, build_tables(events, payments))
