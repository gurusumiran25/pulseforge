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
