# Event catalogue — schema version 1

| Event | Required event-specific properties (initial proposal) |
|---|---|
| page_view | page_path |
| search_performed | search_category, result_count |
| product_viewed | product_id, category, price, currency |
| add_to_cart | product_id, quantity, unit_price, currency |
| checkout_started | cart_value, item_count, currency |
| payment_succeeded | order_id, amount, currency, payment_method_category |
| payment_failed | order_id, failure_code_category |
| order_refunded | order_id, refund_amount, currency, reason_category |

All events use the versioned envelope in `contracts/events/event_envelope_v1.json`. Properties above are an initial implementation proposal to refine in Phase 1. Never include real personal data.
