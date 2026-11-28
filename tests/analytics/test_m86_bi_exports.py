import csv
import io
import pytest
from services.analytics.bi_exports import build_tables, publish_bi

def event(i, name, user="synthetic_returning_001"):
    return dict(event_id=f"00000000-0000-4000-8000-{i:012d}", event_name=name,
                session_id="session_abcdef123456", user_id=user,
                event_time="2026-11-28T12:00:00+00:00")

def payment(e, currency="INR", amount="100.25"):
    return dict(e, currency=currency, amount=amount)

def rows(tables, name):
    return list(csv.DictReader(io.StringIO(tables[name].decode())))

def test_export_grains_and_payment_parity(tmp_path):
    events = [event(1,"product_viewed"),event(2,"add_to_cart"),
              event(3,"checkout_started"),event(4,"payment_succeeded"),
              event(5,"order_refunded"),event(6,"payment_failed")]
    payments = [payment(events[3]),payment(events[4],amount="20.25")]
    tables = build_tables(events,payments)
    assert len(tables)==7
    assert len(rows(tables,"FactEvent.csv"))==6
    session = rows(tables,"FactSession.csv")[0]
    assert session["completed_payment"]=="1"
    assert session["event_count"]=="6"
    assert len(rows(tables,"FactPayment.csv"))==2
    assert rows(tables,"FactDailyUser.csv")[0]["sessions"]=="1"
    assert rows(tables,"DimCurrency.csv")==[{"currency":"INR"}]
    assert publish_bi(tmp_path,events,payments)==publish_bi(tmp_path,list(reversed(events)),list(reversed(payments)))

def test_reject_missing_duplicate_and_orphan_payments():
    e=event(1,"payment_succeeded")
    for payments in ([],[payment(e),payment(e)],[payment(event(2,"payment_succeeded"))]):
        with pytest.raises(ValueError):
            build_tables([e],payments)

def test_reject_non_synthetic_user_and_duplicate_events():
    e=event(1,"page_view")
    with pytest.raises(ValueError):
        build_tables([event(1,"page_view","real_user")],[])
    with pytest.raises(ValueError):
        build_tables([e,e],[])

@pytest.mark.parametrize("amount",["NaN","Infinity","-1"])
def test_reject_invalid_amount(amount):
    e=event(1,"payment_succeeded")
    with pytest.raises(ValueError):
        build_tables([e],[payment(e,amount=amount)])

def test_currency_separation():
    a,b=event(1,"payment_succeeded"),event(2,"payment_succeeded")
    tables=build_tables([a,b],[payment(a,"INR"),payment(b,"USD")])
    assert {r["currency"] for r in rows(tables,"FactPayment.csv")}=={"INR","USD"}
