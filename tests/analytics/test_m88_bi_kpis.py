from decimal import Decimal

from services.analytics.bi_kpis import reference_kpis


def tables(mixed=False, empty=False):
    return {
        "FactSession.csv": b"completed_payment\n" + (b"" if empty else b"1\n0\n"),
        "FactEvent.csv": b"event_name\n" + (b"" if empty else b"payment_succeeded\npayment_failed\norder_refunded\n"),
        "FactPayment.csv": b"currency,event_name,amount\n" + (b"" if empty else b"INR,payment_succeeded,100.25\nINR,order_refunded,20.10\n") + (b"USD,payment_succeeded,12.50\n" if mixed else b""),
        "DimCurrency.csv": b"currency\n" + (b"" if empty else b"INR\n") + (b"USD\n" if mixed else b""),
    }


def test_conversion_and_failure_rate():
    k = reference_kpis(tables())
    assert (k["sessions"], k["events"], k["paid_sessions"]) == (2, 3, 1)
    assert k["conversion"] == k["payment_failure_rate"] == Decimal("0.5")
    assert k["successful_payments"] == k["failed_payments"] == 1


def test_refund_precision():
    k = reference_kpis(tables())
    assert k["gross_revenue"] == Decimal("100.25")
    assert k["refund_amount"] == Decimal("20.10")
    assert k["net_revenue"] == Decimal("80.15")


def test_currency_isolation():
    t = tables(mixed=True)
    assert reference_kpis(t)["net_revenue"] is None
    assert reference_kpis(t, "INR")["net_revenue"] == Decimal("80.15")
    assert reference_kpis(t, "USD")["net_revenue"] == Decimal("12.50")
    assert reference_kpis(t, "EUR")["net_revenue"] is None


def test_empty_dataset():
    k = reference_kpis(tables(empty=True))
    assert k["sessions"] == k["events"] == 0
    assert k["conversion"] is None
    assert k["payment_failure_rate"] is None
    assert k["net_revenue"] is None


from services.analytics.bi_kpis import customer_window, observed_retention


def customer_tables():
    return {
        "FactEvent.csv": b"user_id,date_utc,event_name\na,2026-11-01,payment_succeeded\na,2026-11-07,payment_succeeded\na,2026-11-08,payment_succeeded\nb,2026-11-09,payment_succeeded\n",
        "FactPayment.csv": b"user_id,date_utc,currency,event_name,amount\na,2026-11-08,INR,payment_succeeded,100\na,2026-11-09,INR,order_refunded,20\na,2026-11-07,USD,payment_succeeded,12\nb,2026-11-09,INR,payment_succeeded,500\n",
        "DimDate.csv": b"date_utc\n2026-11-01\n2026-11-09\n",
        "FactDailyUser.csv": b"user_id,date_utc\na,2026-11-01\na,2026-11-02\na,2026-11-08\nb,2026-11-01\nc,2026-11-09\n",
    }


def test_rfm_customer_and_currency_isolation():
    t = customer_tables()
    assert customer_window(t, "a", "2026-11-01", "2026-11-09", "INR") == {
        "recency": 1, "frequency": 3, "monetary": Decimal("80"), "segment": "Recent repeat buyer"}
    assert customer_window(t, "a", "2026-11-01", "2026-11-09", "USD")["monetary"] == Decimal("12")


def test_rfm_no_purchase_and_window():
    t = customer_tables()
    assert customer_window(t, "c", "2026-11-01", "2026-11-09", "INR")["segment"] == "No observed purchase"
    assert customer_window(t, "a", "2026-11-01", "2026-11-02", "INR")["frequency"] == 1


def test_observed_cohort_maturity():
    t = customer_tables()
    assert observed_retention(t, "2026-11-01", 1) == Decimal("0.5")
    assert observed_retention(t, "2026-11-01", 3) == Decimal("0")
    assert observed_retention(t, "2026-11-01", 7) == Decimal("0.5")
    assert observed_retention(t, "2026-11-09", 1) is None
    assert observed_retention(t, "2026-11-03", 1) is None
