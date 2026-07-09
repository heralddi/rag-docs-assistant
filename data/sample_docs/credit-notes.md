# Credit notes

A credit note is the auditable way to reduce the amount of a finalized invoice. Because open and paid invoices are immutable, corrections happen through credit notes rather than edits, which keeps the numbering sequence and the customer's records consistent.

## The credit note object

```json
{
  "id": "cn_2vD8pQk4",
  "object": "credit_note",
  "invoice": "inv_8kQ2mVx",
  "customer": "cus_3nXp7Kd9",
  "status": "issued",
  "amount": 2900,
  "currency": "usd",
  "reason": "order_change",
  "lines": [
    { "description": "Seat removed mid-cycle", "amount": 2900 }
  ],
  "created": "2026-06-10T14:02:41Z",
  "livemode": false
}
```

## Credit note statuses

| Status | Meaning |
|---|---|
| `issued` | Applied to the invoice. `amount_due` was reduced, or a refund was queued. |
| `voided` | Reversed. The invoice balance was restored. |

## Issue a credit note

`POST /v1/credit_notes`

| Parameter | Required | Description |
|---|---|---|
| `invoice` | yes | An `open`, `paid`, or `uncollectible` invoice. |
| `lines` | yes | Array of `{description, amount}`. Must sum to `amount`. |
| `amount` | yes | Total credit in the invoice currency. |
| `reason` | no | One of `duplicate`, `order_change`, `product_unsatisfactory`. |

The effect depends on the invoice state. Against an `open` invoice, the credit reduces `amount_due`. Against a `paid` invoice, the credit becomes a refund on the original payment. The credited amount cannot exceed what remains creditable on the invoice; exceeding it returns `422` with code `credit_exceeds_balance`.

Issuing fires the `credit_note.issued` [webhook event](webhooks.md#event-types).

## Void a credit note

`POST /v1/credit_notes/{id}/void`

Reverses an issued credit note and restores the invoice balance. Voiding is only possible while any associated refund is still `pending`; after the refund settles, the credit note is permanent.

## When to use a credit note versus a refund

Use a [refund](payments.md#refund-a-payment) when the invoice was correct but the money should go back, for example a returned order. Use a credit note when the invoice itself overstated the amount owed, for example a quantity error or a negotiated discount applied late. Tax reporting follows the invoice, so correcting the invoice through a credit note also corrects the [tax](tax.md) totals.
