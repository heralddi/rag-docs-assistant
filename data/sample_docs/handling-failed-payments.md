# Guide: handling failed payments

Some payments fail. Cards expire, balances run dry, issuers decline. This guide sets up a recovery flow, called dunning, that retries intelligently, keeps the customer informed, and decides when to give up. The goal is to recover revenue without burning goodwill.

## How Meridian behaves by default

When a payment for a subscription invoice fails, Meridian marks the subscription `past_due`, fires the `payment.failed` [webhook event](webhooks.md#event-types), and schedules automatic retries on day 3, day 5, and day 7 after the failure. If the final retry fails, the invoice is marked `uncollectible` and the subscription is `canceled`. Everything below customizes this default.

## Step 1: listen for payment.failed

Register a [webhook endpoint](webhooks.md#webhook-endpoints) subscribed to `payment.failed`, `payment.succeeded`, and `subscription.canceled`. The event's `data.object` is the payment, including the invoice ID and the `failure_code`.

Branch on `failure_code` before doing anything else:

| failure_code | What to do |
|---|---|
| `processing_error` | Nothing. The automatic retry will almost certainly succeed. |
| `insufficient_funds` | Let the retry schedule run. Notify the customer after the second failure. |
| `card_expired` | Skip retries. Email a payment-method update link immediately. |
| `authentication_required` | Skip retries. Send the hosted payment link; the customer must authenticate. |
| `card_declined` | Let the schedule run, notify after the first failure. |

Retrying a `card_expired` payment on the same card wastes retry budget and can trigger issuer fraud flags.

## Step 2: customize the retry schedule

Configure retries per account in the Dashboard under Billing, then Dunning, or via the API:

`POST /v1/billing_settings`

```json
{
  "dunning": {
    "retry_schedule_days": [3, 5, 7, 10],
    "on_exhaustion": "mark_uncollectible"
  }
}
```

| Parameter | Description |
|---|---|
| `retry_schedule_days` | Days after failure to retry. Up to 8 entries, max 30 days out. |
| `on_exhaustion` | `mark_uncollectible` (default) also cancels the subscription. `leave_open` keeps the invoice open and the subscription `past_due` for manual handling. |

Weekly retries recover little after day 10; most successful recoveries happen in the first week, so front-load the schedule.

## Step 3: retry manually after the customer acts

When the customer updates their card, do not wait for the next scheduled retry. Trigger collection immediately with a manual [payment](payments.md#create-a-payment):

```bash
curl https://api.meridianbilling.com/v1/payments \
  -H "Authorization: Bearer mb_test_51hGx..." \
  -H "Content-Type: application/json" \
  -d '{"invoice": "inv_8kQ2mVx"}'
```

A successful manual payment clears the invoice, returns the subscription to `active`, and cancels any remaining scheduled retries.

## Step 4: decide what exhaustion means for you

`mark_uncollectible` suits self-serve products: access ends, the books close, and the invoice can still be paid later if the customer returns. `leave_open` suits sales-led contracts where a human follows up, since it preserves the `past_due` state your account team queries. Whichever you choose, reconcile `uncollectible` invoices monthly; they remain payable and occasionally recover on their own.

## Testing the flow

In test mode, create a payment with the magic amount `4002` (in any currency) to force `failure_code: "card_declined"`, or `4069` to force `card_expired`. Magic amounts work only in test mode and are listed in full in the Dashboard's testing reference.
