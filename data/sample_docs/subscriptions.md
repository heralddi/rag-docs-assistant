# Subscriptions

A subscription bills a customer for one or more prices on a recurring schedule. At the end of every billing period, Meridian generates an [invoice](invoices.md) from the subscription and attempts collection.

## The subscription object

```json
{
  "id": "sub_9wF4tBn2",
  "object": "subscription",
  "customer": "cus_3nXp7Kd9",
  "status": "active",
  "items": [
    { "price": "prc_5sRj2Xa8", "quantity": 3 }
  ],
  "current_period_start": "2026-06-01T00:00:00Z",
  "current_period_end": "2026-07-01T00:00:00Z",
  "cancel_at_period_end": false,
  "trial_end": null,
  "created": "2026-04-11T08:25:02Z",
  "livemode": false
}
```

## Subscription statuses

| Status | Meaning |
|---|---|
| `trialing` | In a free trial. Invoicing starts at `trial_end`. |
| `active` | Billing normally. |
| `past_due` | The latest invoice failed collection and dunning is in progress. |
| `paused` | Billing suspended by you. No invoices are generated. |
| `canceled` | Terminal state. The subscription no longer bills. |

A `past_due` subscription returns to `active` when its open invoice is paid, and moves to `canceled` if dunning is exhausted. See [Handling failed payments](handling-failed-payments.md).

## Create a subscription

`POST /v1/subscriptions`

| Parameter | Required | Description |
|---|---|---|
| `customer` | yes | ID of an existing customer. |
| `items` | yes | Array of `{price, quantity}`. At least one item. |
| `trial_days` | no | Integer 1 to 90. Creates the subscription in `trialing`. |
| `proration_behavior` | no | `create_prorations` (default) or `none`. |
| `metadata` | no | Key-value strings. |

```bash
curl https://api.meridianbilling.com/v1/subscriptions \
  -H "Authorization: Bearer mb_test_51hGx..." \
  -H "Content-Type: application/json" \
  -d '{"customer": "cus_3nXp7Kd9", "items": [{"price": "prc_5sRj2Xa8", "quantity": 3}]}'
```

The first invoice is generated immediately unless `trial_days` is set.

## Update a subscription

`POST /v1/subscriptions/{id}`

Changing `items` mid-period creates proration line items on the next invoice by default: a credit for unused time on the old quantity and a charge for remaining time on the new one. Set `proration_behavior` to `none` to bill the new configuration only from the next period.

## Pause and resume

`POST /v1/subscriptions/{id}/pause` and `POST /v1/subscriptions/{id}/resume`

Pausing takes effect immediately: the current period ends, a final prorated invoice is issued, and no further invoices are generated until resume. Resuming starts a fresh billing period at the resume time. Pause is only valid from `active`; pausing a `past_due` subscription returns `422` with code `subscription_not_active`.

## Cancel a subscription

`DELETE /v1/subscriptions/{id}`

| Parameter | Description |
|---|---|
| `at_period_end` | Boolean, default `false`. If `true`, sets `cancel_at_period_end` and the subscription stays `active` until the period closes. |

Immediate cancellation issues a final prorated invoice for the elapsed portion of the period. Cancellation is terminal; to bill the customer again, create a new subscription. Fires the `subscription.canceled` [webhook event](webhooks.md#event-types).
