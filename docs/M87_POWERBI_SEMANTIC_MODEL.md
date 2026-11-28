# M87 Power BI semantic model contract

Status: authored design, not a deployed semantic model.

Use import mode with one immutable snapshot ID per refresh. All relationships below are active, one-to-many, single-direction dimension to fact. No fact-to-fact relationships.

| Dimension key | Fact tables / foreign key |
|---|---|
| DimDate.date_utc | FactEvent, FactSession, FactPayment, FactDailyUser, FactProductView / date_utc |
| DimCustomer.user_id | FactEvent, FactSession, FactPayment, FactDailyUser, FactProductView / user_id |
| DimCurrency.currency | FactPayment / currency |
| DimProduct.product_id | FactProductView / product_id |

Grains: FactEvent event_id; FactSession session_id; FactPayment event_id; FactDailyUser (date_utc,user_id); FactProductView event_id. Date is UTC activity date except FactSession, where it is UTC session start. Date dimension must be expanded to contiguous dates in Power Query and marked as a date table. Use text keys, date type for date_utc, UTC-normalized timestamps, whole numbers for flags/counts, fixed decimal for amounts after precision validation. Hide technical keys from report consumers.

Product filters affect product views only. Do not imply product revenue or conversion without validated attribution. Currency filters affect payment amounts only. Monetary measures return blank when multiple currencies are in context. Payment failure counts come from FactEvent, not FactPayment. Retention and RFM are limited to the rolling synthetic observation window, not lifetime customer history. Refunds are separate positive amounts subtracted from successful payments.

Acceptance: unique non-null dimension keys, complete foreign keys, exact fact grain, no ambiguous filter paths, KPI parity with dbt and Streamlit, and native model validation before release.
