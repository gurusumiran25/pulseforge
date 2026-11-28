# M88 core DAX measure definitions

Authoring source; create these as individual measures in Power BI. Requires M87 relationships and numeric flags.

```dax
Events = COUNTROWS(FactEvent)
Sessions = COUNTROWS(FactSession)
Customers = DISTINCTCOUNT(FactEvent[user_id])
Product View Sessions = SUM(FactSession[viewed_product])
Cart Sessions = SUM(FactSession[added_to_cart])
Checkout Sessions = SUM(FactSession[started_checkout])
Paid Sessions = SUM(FactSession[completed_payment])
Purchase Conversion = DIVIDE([Paid Sessions], [Sessions])
Cart Addition Rate = DIVIDE([Cart Sessions], [Sessions])
Checkout Rate = DIVIDE([Checkout Sessions], [Sessions])
Successful Payments = CALCULATE(COUNTROWS(FactEvent), FactEvent[event_name] = "payment_succeeded")
Failed Payments = CALCULATE(COUNTROWS(FactEvent), FactEvent[event_name] = "payment_failed")
Payment Failure Rate = DIVIDE([Failed Payments], [Failed Payments] + [Successful Payments])
Gross Revenue = IF(HASONEVALUE(DimCurrency[currency]), CALCULATE(SUM(FactPayment[amount]), FactPayment[event_name] = "payment_succeeded"))
Refund Amount = IF(HASONEVALUE(DimCurrency[currency]), CALCULATE(SUM(FactPayment[amount]), FactPayment[event_name] = "order_refunded"))
Net Revenue = IF(HASONEVALUE(DimCurrency[currency]), COALESCE([Gross Revenue],0) - COALESCE([Refund Amount],0))
Product Views = COUNTROWS(FactProductView)
Product Viewers = DISTINCTCOUNT(FactProductView[user_id])
Product Viewing Sessions = DISTINCTCOUNT(FactProductView[session_id])
Active Customer Days = COUNTROWS(FactDailyUser)
```

Format rates as percentages. Display selected currency alongside amounts; never sum currencies. Session conversion is observed session-level completion, not ordered funnel attribution. Product measures respond to product filters; general session and revenue measures do not. Event date and session-start date have distinct semantics. Customer counts represent the selected observation window.

Native DAX engine execution and parity tests are pending. Retention and RFM require separate cohort and customer-window definitions.
