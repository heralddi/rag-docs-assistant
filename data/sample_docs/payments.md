# Payments

A payment is one attempt to collect an invoice balance from a customer's payment method. Payments are usually created automatically when an invoice with `auto_collect` finalizes; you can also trigger them manually.

## The payment object

```json
{
  "id": "pay_6cJm3Wq7",
  "object": "payment",
  "invoice": "inv_8kQ2mVx",
  "customer": "cus_3nXp7Kd9",
  "status": "succeeded",
  "amount": 9441,
  "currency": "usd",
  "payment_method": "card",
  "failure_code": null,
  "created": "2026-06-01T01:00:12Z",
  "livemode": false
}
```

## Payment statuses

| Status | Meaning |
|---|---|
| `pending` | Submitted to the payment network, result not yet known. |
| `succeeded` | Funds captured. The invoice `amount_due` is reduced. |
| `failed` | The attempt failed. `failure_code` explains why. |
| `refunded` | Previously succeeded, then fully refunded. |

Bank-transfer payments can stay `pending` for several business days. Listen for the `payment.succeeded` and `payment.failed` [webhook events](webhooks.md#event-types) instead of polling.

## Create a payment

`POST /v1/payments`

Manually attempts collection of an open invoice, for example to retry after a failure once the customer has updated their card.

| Parameter | Required | Description |
|---|---|---|
| `invoice` | yes | ID of an `open` or `uncollectible` invoice. |
| `amount` | no | Defaults to the invoice `amount_due`. Partial amounts allowed. |

A payment against a `paid` or `void` invoice returns `422` with code `invoice_not_payable`.

## Payment failure codes

When `status` is `failed`, `failure_code` holds one of:

| Code | Meaning | Suggested handling |
|---|---|---|
| `card_declined` | Generic decline by the issuer. | Retry per your dunning schedule. |
| `insufficient_funds` | Not enough balance. | Retry after a few days. |
| `card_expired` | The stored card is out of date. | Ask the customer for a new card. |
| `authentication_required` | The issuer demands 3-D Secure. | Send the customer a hosted payment link. |
| `processing_error` | Transient network or processor error. | Safe to retry immediately, once. |

For the full recovery playbook, see [Handling failed payments](handling-failed-payments.md).

## Refund a payment

`POST /v1/payments/{id}/refund`

| Parameter | Required | Description |
|---|---|---|
| `amount` | no | Defaults to the full remaining refundable amount. |
| `reason` | no | One of `requested_by_customer`, `duplicate`, `fraudulent`. |

Refunding reopens the invoice balance by the refunded amount. A refund does not create a credit note; if the customer's invoice total was wrong in the first place, issue a [credit note](credit-notes.md) so the paper trail stays correct.
