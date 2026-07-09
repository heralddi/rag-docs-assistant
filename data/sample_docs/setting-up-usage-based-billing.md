# Guide: setting up usage-based billing

This guide walks through billing a customer for metered usage, such as API calls or gigabytes stored, instead of a flat seat count. You will create a metered price, subscribe a customer to it, report usage during the period, and verify the resulting invoice. Work in test mode throughout; switch to your live key only at the end.

## Prerequisites

- A test secret key (`mb_test_`). See [Authentication](authentication.md).
- A [customer](customers.md) to bill. The examples use `cus_3nXp7Kd9`.

## Step 1: create a metered price

A metered price has no fixed quantity. Instead, the quantity is the usage you report during the billing period.

`POST /v1/prices`

```bash
curl https://api.meridianbilling.com/v1/prices \
  -H "Authorization: Bearer mb_test_51hGx..." \
  -H "Content-Type: application/json" \
  -d '{
    "nickname": "API calls, per 1000",
    "unit_amount": 40,
    "currency": "usd",
    "interval": "month",
    "usage_type": "metered",
    "transform_quantity": {"divide_by": 1000, "round": "up"}
  }'
```

`usage_type: "metered"` is what makes the price usage-based. `transform_quantity` bills per 1000 reported units, rounding up, so 12,300 calls bill as 13 units of 40 cents.

## Step 2: subscribe the customer

Create the subscription as usual, but omit `quantity` on the metered item:

```bash
curl https://api.meridianbilling.com/v1/subscriptions \
  -H "Authorization: Bearer mb_test_51hGx..." \
  -H "Content-Type: application/json" \
  -d '{"customer": "cus_3nXp7Kd9", "items": [{"price": "prc_9mTk4Zc2"}]}'
```

Note the subscription item ID (`si_` prefix) in the response. Usage reports reference the item, not the subscription.

## Step 3: report usage

Report usage as it happens, or in periodic batches:

`POST /v1/subscription_items/{id}/usage_records`

| Parameter | Required | Description |
|---|---|---|
| `quantity` | yes | Units used since the last report. Positive integer. |
| `timestamp` | no | When the usage occurred. Defaults to now. Must fall inside the current period. |
| `action` | no | `increment` (default) adds to the running total. `set` replaces it. |

Batch reports where you can. One report per user action is the fastest way to hit [rate limits](rate-limits.md); an hourly batch with `action: "increment"` is usually enough resolution. Send an `Idempotency-Key` with every report so a retried batch is not double-counted.

## Step 4: verify the invoice

At period end, the subscription generates a draft [invoice](invoices.md) with one line per metered item, quantity equal to the transformed usage total. The invoice finalizes automatically an hour later.

To check mid-period totals without waiting, fetch the upcoming invoice preview:

```
GET /v1/invoices/upcoming?subscription=sub_9wF4tBn2
```

## Going live

1. Recreate the price with your live key. Object IDs do not transfer between environments.
2. Subscribe live customers and start reporting usage immediately. Usage reported before subscription creation is rejected with `422`.
3. Subscribe to the `invoice.finalized` [webhook event](webhooks.md#event-types) and reconcile each invoice against your own usage logs before it is collected.
