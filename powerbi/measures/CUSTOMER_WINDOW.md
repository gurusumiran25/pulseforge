# M88 customer-window analytics

All measures are evaluated over the selected UTC date window. These are observed-window metrics, not lifetime RFM. Customer revenue requires one selected currency. Recency and frequency use successful payment events regardless of currency; frequency is payment count, not unique orders.

```dax
Window End = MAX(DimDate[date_utc])
Last Purchase Date = CALCULATE(MAX(FactEvent[date_utc]), FactEvent[event_name] = "payment_succeeded")
Recency Days = IF(HASONEVALUE(DimCustomer[user_id]) && NOT ISBLANK([Last Purchase Date]), DATEDIFF([Last Purchase Date], [Window End], DAY))
Purchase Frequency = [Successful Payments]
Monetary Value = [Net Revenue]
RFM Segment = 
    IF(HASONEVALUE(DimCustomer[user_id]) && HASONEVALUE(DimCurrency[currency]),
        SWITCH(TRUE(),
            ISBLANK([Last Purchase Date]), "No observed purchase",
            [Recency Days] <= 3 && [Purchase Frequency] >= 3 && [Monetary Value] > 0, "Recent repeat buyer",
            [Recency Days] <= 3, "Recent buyer",
            [Recency Days] >= 7, "Less recent buyer",
            "Other buyer"))
Repeat Active Customers =
    COUNTROWS(FILTER(VALUES(DimCustomer[user_id]), CALCULATE(DISTINCTCOUNT(FactDailyUser[date_utc])) >= 2))
Observed Active Customers = DISTINCTCOUNT(FactDailyUser[user_id])
Repeat Activity Rate = DIVIDE([Repeat Active Customers], [Observed Active Customers])
```

Repeat activity is not cohort retention. Thresholds are illustrative fixed rules for a 14-day synthetic window, not learned quantiles. Do not compare segments across currencies or different observation lengths without disclosure. Native DAX validation remains required.
