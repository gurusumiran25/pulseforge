# M89 report page specification

Authoring blueprint, not a rendered PBIX. 16:9 canvas, consistent UTC date slicer, accessible labels, teal accent, neutral background. Currency slicer on monetary pages only.

| Page | KPI cards | Visuals |
|---|---|---|
| Executive overview | Sessions, Customers, Purchase Conversion, Net Revenue | Daily session trend, conversion funnel, revenue trend by selected currency |
| Customer journey | Product View Sessions, Cart Sessions, Checkout Sessions, Paid Sessions | Observed session funnel, daily conversion trend, event breakdown |
| Payments | Successful Payments, Failed Payments, Payment Failure Rate, Refund Amount | Payment outcomes trend, gross/refund/net by date and selected currency |
| Customer intelligence | Observed Active Customers, Repeat Activity Rate | Cohort date by offset matrix, customer RFM detail table, active customers trend |
| Product intelligence | Product Views, Product Viewers, Product Viewing Sessions | Category bars, product ranking, product views by date |
| Data quality | Events, Sessions | Daily event counts, snapshot ID and observation window; publisher quality evidence linked externally |
| Insights | Session Growth, Rolling 7 Day Sessions | Current/prior window comparison, trend and analyst interpretation |

Product filters only affect product visuals. Do not display product revenue or conversion attribution. Currency context must be explicit for amounts. Cohort retention uses first observed activity, not acquisition. Quality page must not claim live warehouse health without a separate verified status feed. No fabricated insights; annotate actual observed results after refresh.

Acceptance: native rendering, no broken visuals, slicer and drillthrough tests, readable screenshots, measure parity.
