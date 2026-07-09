# Webhooks

Webhooks push events to your server as they happen, so you do not have to poll. Meridian sends an HTTPS `POST` to your endpoint with an event object in the body whenever something you subscribed to occurs.

## Webhook endpoints

Register endpoints in the Dashboard under Developers, then Webhooks, or via `POST /v1/webhook_endpoints`. Each endpoint has an ID with prefix `whe_`, a URL, and a list of subscribed event types. Registering an endpoint returns a signing secret with prefix `whsec_` exactly once. Store it like an API key; it cannot be retrieved again, only rolled.

| Parameter | Type | Description |
|---|---|---|
| `url` | string | HTTPS URL that receives events. Required. |
| `enabled_events` | array | Event types to deliver, for example `["invoice.finalized", "payment.failed"]`. Use `["*"]` for all types. |
| `description` | string | Free-text label shown in the Dashboard. Optional. |

## The event object

```json
{
  "id": "evt_4tYq8Lm2",
  "object": "event",
  "type": "invoice.finalized",
  "created": "2026-06-02T11:04:53Z",
  "livemode": false,
  "data": {
    "object": { "id": "inv_8kQ2mVx", "object": "invoice", "...": "..." }
  }
}
```

`data.object` is the full resource in the state it had when the event was created. Events are immutable. You can also fetch any event for 30 days at `GET /v1/events/{id}`, which is the recommended way to reconcile after an outage.

## Event types

Event types are named `resource.action`. The most commonly used types:

| Type | Fired when |
|---|---|
| `customer.created` | A customer is created. |
| `subscription.activated` | A subscription leaves `trialing` or is created active. |
| `subscription.canceled` | A subscription is canceled. |
| `invoice.finalized` | An invoice becomes immutable and collectable. |
| `invoice.paid` | An invoice balance reaches zero. |
| `payment.failed` | A payment attempt fails. |
| `credit_note.issued` | A credit note is issued against an invoice. |

## Verifying signatures

Every delivery carries a `Meridian-Signature` header. Verify it before trusting the payload, because anyone can send JSON to your endpoint.

```
Meridian-Signature: t=1767437093,v1=5257a869e7ecebeda32affa62cdca3fa51cad7e77a0e56ff536d0ce8e108d8bd
```

To verify:

1. Split the header on commas into `t` (a Unix timestamp) and `v1` (a hex digest).
2. Concatenate the timestamp, a literal `.`, and the raw request body: `{t}.{body}`.
3. Compute HMAC-SHA256 over that string with your `whsec_` signing secret.
4. Compare your digest to `v1` with a constant-time comparison.
5. Reject the event if `t` is more than 300 seconds from the current time. This blocks replay of captured deliveries.

Compute the HMAC over the raw bytes you received. Parsing the JSON and re-serializing it before signing is the most common cause of verification failures.

## Delivery and retries

Your endpoint must respond with a 2xx status within 10 seconds. Anything else counts as a failed delivery, and Meridian retries with exponential backoff for up to 72 hours: roughly 1 minute, 5 minutes, 30 minutes, 2 hours, and then every 4 hours. After 72 hours of failures the endpoint is disabled and you are notified by email.

Deliveries are at-least-once and can arrive out of order. Make handlers idempotent by recording processed event IDs, and use the `created` timestamp rather than arrival order when ordering matters.

## Handler best practices

- Return `200` immediately and process the event on a queue. Slow handlers cause timeouts, which cause retries, which cause duplicate work.
- Verify the signature before reading any field of the payload.
- Subscribe only to the event types you handle. `["*"]` is convenient in development and noisy in production.
