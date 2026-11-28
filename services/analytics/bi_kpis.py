"""Independent reference calculations for BI measure parity."""
import csv
import io
from decimal import Decimal


def reference_kpis(tables, currency=None):
    def rows(name):
        return list(csv.DictReader(io.StringIO(tables[name + ".csv"].decode())))
    sessions = rows("FactSession")
    events = rows("FactEvent")
    payments = rows("FactPayment")
    def ratio(n, d):
        return Decimal(n) / Decimal(d) if d else None
    def count(name):
        return sum(e["event_name"] == name for e in events)
    success, failed = count("payment_succeeded"), count("payment_failed")
    paid = sum(int(s["completed_payment"]) for s in sessions)
    currencies = {r["currency"] for r in rows("DimCurrency")}
    selected = currency if currency in currencies else None
    if currency is None and len(currencies) == 1:
        selected = next(iter(currencies))
    gross = refunds = net = None
    if selected is not None:
        amounts = [p for p in payments if p["currency"] == selected]
        gross = sum((Decimal(p["amount"]) for p in amounts if p["event_name"] == "payment_succeeded"), Decimal(0))
        refunds = sum((Decimal(p["amount"]) for p in amounts if p["event_name"] == "order_refunded"), Decimal(0))
        net = gross - refunds
    return {"sessions": len(sessions), "events": len(events),
            "paid_sessions": paid, "conversion": ratio(paid, len(sessions)),
            "successful_payments": success, "failed_payments": failed,
            "payment_failure_rate": ratio(failed, success + failed),
            "gross_revenue": gross, "refund_amount": refunds, "net_revenue": net}


def customer_window(tables, user_id, start, end, currency):
    from datetime import date
    def rows(name):
        return list(csv.DictReader(io.StringIO(tables[name + ".csv"].decode())))
    purchases = [r for r in rows("FactEvent") if r["user_id"] == user_id
                 and start <= r["date_utc"] <= end and r["event_name"] == "payment_succeeded"]
    payments = [r for r in rows("FactPayment") if r["user_id"] == user_id
                and start <= r["date_utc"] <= end and r["currency"] == currency]
    monetary = sum((Decimal(r["amount"]) * (1 if r["event_name"] == "payment_succeeded" else -1)
                    for r in payments if r["event_name"] in {"payment_succeeded", "order_refunded"}), Decimal(0))
    recency = (date.fromisoformat(end) - date.fromisoformat(max(r["date_utc"] for r in purchases))).days if purchases else None
    segment = ("No observed purchase" if recency is None else
               "Recent repeat buyer" if recency <= 3 and len(purchases) >= 3 and monetary > 0 else
               "Recent buyer" if recency <= 3 else "Less recent buyer" if recency >= 7 else "Other buyer")
    return {"recency": recency, "frequency": len(purchases), "monetary": monetary, "segment": segment}


def observed_retention(tables, cohort_date, offset):
    from datetime import date, timedelta
    def rows(name):
        return list(csv.DictReader(io.StringIO(tables[name + ".csv"].decode())))
    if offset not in range(1, 8):
        raise ValueError("Offset must be 1 through 7")
    target = (date.fromisoformat(cohort_date) + timedelta(days=offset)).isoformat()
    dates = [r["date_utc"] for r in rows("DimDate")]
    if not dates or cohort_date < min(dates) or target > max(dates):
        return None
    activity = {}
    for row in rows("FactDailyUser"):
        activity.setdefault(row["user_id"], set()).add(row["date_utc"])
    members = [days for days in activity.values() if min(days) == cohort_date]
    return Decimal(sum(target in days for days in members)) / Decimal(len(members)) if members else None


def period_metrics(tables, start, end):
    from datetime import date, timedelta
    def rows(name):
        return list(csv.DictReader(io.StringIO(tables[name + ".csv"].decode())))
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if start > end:
        raise ValueError("Invalid date window")
    dates = [date.fromisoformat(r["date_utc"]) for r in rows("DimDate")]
    sessions = [date.fromisoformat(r["date_utc"]) for r in rows("FactSession")]
    if not dates or start < min(dates) or end > max(dates):
        raise ValueError("Window outside snapshot")
    def count(lo, hi):
        return sum(lo <= d <= hi for d in sessions)
    days = (end - start).days + 1
    current = count(start, end)
    prior_start = start - timedelta(days=days)
    prior = count(prior_start, start - timedelta(days=1)) if prior_start >= min(dates) else None
    rolling_start = end - timedelta(days=6)
    rolling = Decimal(count(rolling_start, end)) / 7 if rolling_start >= min(dates) else None
    return {"sessions": current, "prior_sessions": prior,
            "session_growth": Decimal(current - prior) / prior if prior else None,
            "rolling_7_day_average": rolling}
